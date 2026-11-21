import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from config.env import load_env

load_env()

logger = logging.getLogger("fedhealth.security")


# ================= JWT CONFIGURATION =================

def _load_secret() -> str:
    secret = os.getenv("FEDHEALTH_JWT_SECRET", "").strip()
    if secret:
        return secret

    logger.warning(
        "FEDHEALTH_JWT_SECRET is not set. Using a random secret for this "
        "process only; all logins will be invalidated on restart. "
        "Set it in .env for a stable secret."
    )
    return secrets.token_urlsafe(48)


SECRET_KEY = _load_secret()

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("FEDHEALTH_TOKEN_MINUTES", "60")
)


# ================= ROLES =================

ADMIN = "admin"
DOCTOR = "doctor"
NURSE = "nurse"
RECEPTIONIST = "receptionist"
LAB_TECHNICIAN = "lab_technician"

ALL_ROLES = (ADMIN, DOCTOR, NURSE, RECEPTIONIST, LAB_TECHNICIAN)


# ================= PASSWORD HASHING =================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# ================= CREATE JWT TOKEN =================

def create_access_token(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ================= VERIFY JWT TOKEN =================

def verify_access_token(token: str):
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

    except ExpiredSignatureError:
        logger.info("JWT rejected: token expired")
        return None

    except JWTError:
        logger.info("JWT rejected: invalid token")
        return None


# ================= GET CURRENT USER =================

security_scheme = HTTPBearer()


def user_from_payload(payload):
    """Turn a decoded JWT payload into a user dict, or None if invalid."""
    if not payload:
        return None

    user_id = payload.get("sub")
    role = payload.get("role")
    hospital_id = payload.get("hospital_id")

    if not user_id or not role or not hospital_id:
        return None

    try:
        return {
            "user_id": int(user_id),
            "role": role,
            "hospital_id": int(hospital_id)
        }
    except (TypeError, ValueError):
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security_scheme
    )
):
    user = user_from_payload(
        verify_access_token(credentials.credentials)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


# ================= ROLE-BASED ACCESS CONTROL =================

def require_roles(*allowed_roles):
    """Dependency factory: only the listed roles may continue."""

    def role_checker(
        current_user: dict = Depends(get_current_user)
    ):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )

        return current_user

    return role_checker


def method_roles(read, write, delete=None):
    """Dependency factory with different roles for reading and writing.

    ``read``   roles allowed for GET
    ``write``  roles allowed for POST / PUT / PATCH
    ``delete`` roles allowed for DELETE (defaults to ``write``)
    """
    delete = write if delete is None else delete

    def checker(
        request: Request,
        current_user: dict = Depends(get_current_user)
    ):
        method = request.method.upper()

        if method in ("GET", "HEAD"):
            allowed = read
        elif method == "DELETE":
            allowed = delete
        else:
            allowed = write

        if current_user["role"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )

        return current_user

    return checker


# ================= HOSPITAL SCOPE =================

def hospital_scope(
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    """A user may only touch the hospital they logged in to."""
    if hospital_id != current_user["hospital_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access another hospital's data"
        )

    return current_user
