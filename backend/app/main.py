import logging
import os
import sys
from pathlib import Path

# --------------------------------------------------
# IMPORT PATHS
# Makes both of these work:
#   python -m uvicorn backend.app.main:app   (from the project root)
#   python -m uvicorn app.main:app           (from the backend folder)
# --------------------------------------------------

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _path in (str(_PROJECT_ROOT), str(_BACKEND_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from config.env import load_env

load_env()

from app.core.audit import log_audit
from app.core.security import (
    ADMIN,
    ALL_ROLES,
    DOCTOR,
    LAB_TECHNICIAN,
    NURSE,
    RECEPTIONIST,
    get_current_user,
    hospital_scope,
    method_roles,
    require_roles,
    user_from_payload,
    verify_access_token,
)

from app.api.routes.ai_predictions import router as ai_predictions_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.database import router as database_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.federated import router as federated_router
from app.api.routes.hospitals import router as hospitals_router
from app.api.routes.lab_orders import router as lab_orders_router
from app.api.routes.lab_reports import router as lab_reports_router
from app.api.routes.medical_records import router as medical_records_router
from app.api.routes.os_monitoring import router as os_router
from app.api.routes.patients import router as patients_router
from app.api.routes.prescriptions import router as prescriptions_router
from app.api.routes.users import router as users_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="FedHealth API",
    description="Hospital Management and Federated Healthcare System",
    version="1.1.0"
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FEDHEALTH_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"]
)


# --------------------------------------------------
# AUDIT MIDDLEWARE
# Records every data change, and every read of clinical records,
# made with a valid token and answered successfully.
# --------------------------------------------------

AUDITED_READ_PREFIXES = (
    "/api/patients",
    "/api/medical-records",
    "/api/prescriptions",
    "/api/lab-orders",
    "/api/lab-reports",
    "/api/ai-predictions",
)

METHOD_ACTIONS = {
    "POST": "CREATE",
    "PUT": "UPDATE",
    "PATCH": "UPDATE",
    "DELETE": "DELETE",
    "GET": "VIEW",
}


def _audit_request(request: Request, status_code: int):
    path = request.url.path

    if status_code >= 400 or path.startswith("/api/auth"):
        return

    method = request.method.upper()

    if method == "GET" and not path.startswith(AUDITED_READ_PREFIXES):
        return

    if method not in METHOD_ACTIONS:
        return

    header = request.headers.get("authorization", "")

    if not header.lower().startswith("bearer "):
        return

    user = user_from_payload(verify_access_token(header[7:].strip()))

    if user is None:
        return

    parts = [part for part in path.split("/") if part]
    entity_type = parts[1].replace("-", "_") if len(parts) > 1 else None
    entity_id = parts[2] if len(parts) > 2 else None

    # /api/<resource>/patient/<id> -> the id is the patient id
    if entity_id == "patient" and len(parts) > 3:
        entity_id = parts[3]

    log_audit(
        user["hospital_id"],
        user["user_id"],
        f"{METHOD_ACTIONS[method]}_{(entity_type or 'resource').upper()}",
        entity_type,
        entity_id,
        {"method": method, "path": path}
    )


@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    response = await call_next(request)

    if request.method != "OPTIONS":
        await run_in_threadpool(
            _audit_request, request, response.status_code
        )

    return response


# --------------------------------------------------
# REGISTER ROUTERS
# Access rules (role + hospital scope) are applied here, per router.
# --------------------------------------------------

CLINICAL = [Depends(hospital_scope)]

STAFF = (ADMIN, DOCTOR, NURSE)
FRONT_DESK = (ADMIN, RECEPTIONIST, DOCTOR, NURSE)

app.include_router(auth_router)
app.include_router(
    users_router,
    dependencies=[Depends(require_roles(ADMIN))]
)

# Patients, doctors and appointments also check hospital scope inside the
# router; the dependencies here add role rules per HTTP method.
app.include_router(
    patients_router,
    dependencies=[Depends(method_roles(
        read=ALL_ROLES, write=FRONT_DESK, delete=(ADMIN,)
    ))]
)
app.include_router(
    doctors_router,
    dependencies=[Depends(method_roles(
        read=ALL_ROLES, write=(ADMIN,)
    ))]
)
app.include_router(
    appointments_router,
    dependencies=[Depends(method_roles(
        read=ALL_ROLES, write=FRONT_DESK, delete=(ADMIN, RECEPTIONIST)
    ))]
)

app.include_router(
    medical_records_router,
    dependencies=[Depends(method_roles(
        read=STAFF, write=STAFF, delete=(ADMIN,)
    ))] + CLINICAL
)
app.include_router(
    prescriptions_router,
    dependencies=[Depends(method_roles(
        read=STAFF, write=(ADMIN, DOCTOR), delete=(ADMIN,)
    ))] + CLINICAL
)
app.include_router(
    lab_orders_router,
    dependencies=[Depends(method_roles(
        read=STAFF + (LAB_TECHNICIAN,),
        write=STAFF + (LAB_TECHNICIAN,),
        delete=(ADMIN,)
    ))] + CLINICAL
)
app.include_router(
    lab_reports_router,
    dependencies=[Depends(method_roles(
        read=STAFF + (LAB_TECHNICIAN,),
        write=(ADMIN, DOCTOR, LAB_TECHNICIAN),
        delete=(ADMIN,)
    ))] + CLINICAL
)
app.include_router(
    ai_predictions_router,
    dependencies=[Depends(require_roles(ADMIN, DOCTOR))] + CLINICAL
)

# Any logged-in user
app.include_router(
    dashboard_router, dependencies=[Depends(get_current_user)]
)
app.include_router(
    hospitals_router, dependencies=[Depends(get_current_user)]
)

# Admin-only (roles enforced inside the routers)
app.include_router(database_router)
app.include_router(os_router)
app.include_router(audit_router)
app.include_router(federated_router, dependencies=[Depends(get_current_user)])


# --------------------------------------------------
# PUBLIC ENDPOINTS
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Welcome to FedHealth API",
        "status": "running",
        "version": app.version
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "FedHealth backend is running"
    }
