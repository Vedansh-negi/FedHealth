
import logging
import os
import secrets

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from config.env import load_env
from database.hospital_db import get_hospital_connection


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

ALL_ROLES = (
    ADMIN,
    DOCTOR,
    NURSE,
    RECEPTIONIST,
    LAB_TECHNICIAN
)


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
    """
    Convert a decoded JWT payload into a validated user identity.
    Returns None if the payload is invalid.
    """

    if not payload:
        return None

    user_id = payload.get("sub")

    role = payload.get("role")

    hospital_id = payload.get("hospital_id")

    if not user_id or not role or not hospital_id:
        return None

    try:

        user_id = int(user_id)

        hospital_id = int(hospital_id)

        if user_id <= 0 or hospital_id not in (1, 2, 3):
            return None

        return {
            "user_id": user_id,
            "role": role,
            "hospital_id": hospital_id
        }

    except (TypeError, ValueError):

        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security_scheme
    )
):
    """
    Authenticate the JWT and verify the user's current account
    status and role against the corresponding hospital database.
    """

    # Step 1: Validate JWT
    user = user_from_payload(
        verify_access_token(credentials.credentials)
    )

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    connection = None

    try:

        # Step 2: Connect to the authenticated user's hospital database
        connection = get_hospital_connection(
            user["hospital_id"]
        )

        # Step 3: Retrieve current account information
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT role, is_active
                FROM users
                WHERE user_id = %s
                """,
                (user["user_id"],)
            )

            db_user = cursor.fetchone()

        # Step 4: Reject deleted or inactive accounts
        if not db_user or not db_user[1]:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive or no longer exists",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Step 5: Use the current database role
        # instead of trusting the role stored in the JWT
        user["role"] = db_user[0]

        return user

    except HTTPException:

        raise

    except Exception:

        logger.exception(
            "Unable to validate authenticated user against database"
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify user account"
        )

    finally:

        if connection:
            connection.close()


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
    """
    Dependency factory with different roles for reading and writing.

    read   roles allowed for GET
    write  roles allowed for POST / PUT / PATCH
    delete roles allowed for DELETE (defaults to write)
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
    """A user may only access the hospital they logged in to."""

    if hospital_id != current_user["hospital_id"]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access another hospital's data"
        )

    return current_user

