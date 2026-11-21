import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr
from psycopg2.extras import RealDictCursor

from app.core.audit import log_audit
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from database.hospital_db import get_hospital_connection


logger = logging.getLogger("fedhealth.auth")

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


# --------------------------------------------------
# SIMPLE IN-MEMORY LOGIN THROTTLE
# (per email + client IP; resets when the server restarts)
# --------------------------------------------------

MAX_FAILED_ATTEMPTS = 5
WINDOW_SECONDS = 300

_failures = defaultdict(deque)
_lock = threading.Lock()

# A valid bcrypt hash used so that unknown e-mails cost the same time as
# known ones (prevents user enumeration through response timing).
_DUMMY_HASH = hash_password("not-a-real-password")


def _throttle_key(email, request):
    client = request.client.host if request.client else "unknown"
    return f"{email.lower()}|{client}"


def _is_locked(key):
    now = time.monotonic()

    with _lock:
        attempts = _failures[key]

        while attempts and now - attempts[0] > WINDOW_SECONDS:
            attempts.popleft()

        return len(attempts) >= MAX_FAILED_ATTEMPTS


def _record_failure(key):
    with _lock:
        _failures[key].append(time.monotonic())


def _clear_failures(key):
    with _lock:
        _failures.pop(key, None)


# --------------------------------------------------
# MODELS
# --------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@router.post("/login")
def login(
    data: LoginRequest,
    request: Request,
    hospital_id: int = Query(1, ge=1, le=3)
):
    key = _throttle_key(str(data.email), request)

    if _is_locked(key):
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Try again in a few minutes."
        )

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    user_id,
                    full_name,
                    email,
                    password_hash,
                    role,
                    is_active
                FROM users
                WHERE email = %s
                """,
                (str(data.email).strip().lower(),)
            )

            user = cursor.fetchone()

    except HTTPException:
        raise

    except Exception:
        logger.exception("Login database error")
        raise HTTPException(
            status_code=503,
            detail="Login service is temporarily unavailable"
        )

    finally:
        if connection:
            connection.close()

    # Always run a hash comparison, then give one generic error for
    # unknown user / wrong password / inactive account.
    password_ok = verify_password(
        data.password,
        user["password_hash"] if user else _DUMMY_HASH
    )

    if not user or not password_ok or not user["is_active"]:
        _record_failure(key)

        if user:
            log_audit(
                hospital_id,
                user["user_id"],
                "LOGIN_FAILED",
                "user",
                user["user_id"]
            )

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    _clear_failures(key)

    token = create_access_token({
        "sub": str(user["user_id"]),
        "role": user["role"],
        "hospital_id": hospital_id
    })

    log_audit(
        hospital_id,
        user["user_id"],
        "LOGIN",
        "user",
        user["user_id"]
    )

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "hospital_id": hospital_id
        }
    }


# --------------------------------------------------
# CURRENT USER
# --------------------------------------------------

@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user)
):
    return {
        "message": "Authentication successful",
        "user": current_user
    }


# --------------------------------------------------
# CHANGE PASSWORD
# --------------------------------------------------

@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 8 characters"
        )

    connection = None

    try:
        connection = get_hospital_connection(
            current_user["hospital_id"]
        )

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(
                "SELECT password_hash FROM users WHERE user_id = %s",
                (current_user["user_id"],)
            )

            row = cursor.fetchone()

            if not row or not verify_password(
                data.current_password,
                row["password_hash"]
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Current password is incorrect"
                )

            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (
                    hash_password(data.new_password),
                    current_user["user_id"]
                )
            )

        connection.commit()

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()

        logger.exception("Change password error")
        raise HTTPException(
            status_code=500,
            detail="Unable to change password"
        )

    finally:
        if connection:
            connection.close()

    log_audit(
        current_user["hospital_id"],
        current_user["user_id"],
        "PASSWORD_CHANGED",
        "user",
        current_user["user_id"]
    )

    return {"message": "Password changed successfully"}
