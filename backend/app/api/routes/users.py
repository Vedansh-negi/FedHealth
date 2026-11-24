
import logging

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from pydantic import BaseModel, Field, EmailStr

from psycopg2.extras import RealDictCursor

from app.core.security import (
    get_current_user,
    hash_password,
    ALL_ROLES,
)

from app.core.audit import log_audit

from database.hospital_db import get_hospital_connection


logger = logging.getLogger("fedhealth.users")

router = APIRouter(
    prefix="/api/users",
    tags=["User Management"]
)


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    role: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )
    email: Optional[EmailStr] = None
    role: Optional[str] = None


# --------------------------------------------------
# GET ALL USERS
# GET /api/users/
# --------------------------------------------------

@router.get("/")
def get_users(
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    """List users belonging to the authenticated hospital."""

    if current_user["hospital_id"] != hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another hospital's users"
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
                    role,
                    is_active,
                    created_at
                FROM users
                ORDER BY created_at DESC, user_id DESC
                """
            )

            users = cursor.fetchall()

        return {
            "hospital_id": hospital_id,
            "total_users": len(users),
            "users": users
        }

    except Exception:
        logger.exception(
            "Unable to retrieve users for hospital %s",
            hospital_id
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve users"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# CREATE USER
# POST /api/users/
# --------------------------------------------------

@router.post("/", status_code=201)
def create_user(
    data: UserCreate,
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    """Create a new user account in the authenticated hospital."""

    if current_user["hospital_id"] != hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot manage another hospital's users"
        )

    if data.role not in ALL_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Invalid user role"
        )

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            # Check for duplicate email
            normalized_email = str(data.email).strip().lower()

            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                """,
                (normalized_email,)
            )

            if cursor.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail="Email already registered"
                )

            # Create account with hashed password
            cursor.execute(
                """
                INSERT INTO users (
                    full_name,
                    email,
                    password_hash,
                    role,
                    is_active
                )
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING
                    user_id,
                    full_name,
                    email,
                    role,
                    is_active,
                    created_at
                """,
                (
                    data.full_name.strip(),
                    normalized_email,
                    hash_password(data.password),
                    data.role
                )
            )

            new_user = cursor.fetchone()

        connection.commit()

        # Audit log
        log_audit(
            hospital_id,
            current_user["user_id"],
            "USER_CREATED",
            "user",
            new_user["user_id"]
        )

        return {
            "message": "User created successfully",
            "user": new_user
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()

        logger.exception("User creation failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to create user"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# UPDATE USER
# PUT /api/users/{user_id}
# --------------------------------------------------

@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdate,
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    """Update a user's name, email, or role."""

    if current_user["hospital_id"] != hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot manage another hospital's users"
        )

    updates = data.dict(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update"
        )

    if "role" in updates and updates["role"] not in ALL_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Invalid user role"
        )

    # Prevent an administrator from demoting themselves.
    if (
        user_id == current_user["user_id"]
        and updates.get("role") not in (None, "admin")
    ):
        raise HTTPException(
            status_code=400,
            detail="You cannot remove your own administrator role"
        )

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            # Retrieve existing user and lock the row
            cursor.execute(
                """
                SELECT
                    user_id,
                    full_name,
                    email,
                    role,
                    is_active
                FROM users
                WHERE user_id = %s
                FOR UPDATE
                """,
                (user_id,)
            )

            existing_user = cursor.fetchone()

            if not existing_user:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )

            new_name = updates.get(
                "full_name",
                existing_user["full_name"]
            )

            new_email = str(
                updates.get("email", existing_user["email"])
            ).strip().lower()

            new_role = updates.get(
                "role",
                existing_user["role"]
            )

            # Check duplicate email, excluding this user
            if new_email != existing_user["email"].lower():

                cursor.execute(
                    """
                    SELECT user_id
                    FROM users
                    WHERE LOWER(email) = LOWER(%s)
                    AND user_id <> %s
                    """,
                    (new_email, user_id)
                )

                if cursor.fetchone():
                    raise HTTPException(
                        status_code=409,
                        detail="Email already exists"
                    )

            # Update user
            cursor.execute(
                """
                UPDATE users
                SET
                    full_name = %s,
                    email = %s,
                    role = %s
                WHERE user_id = %s
                RETURNING
                    user_id,
                    full_name,
                    email,
                    role,
                    is_active,
                    created_at
                """,
                (
                    new_name,
                    new_email,
                    new_role,
                    user_id
                )
            )

            updated_user = cursor.fetchone()

        connection.commit()

        # Audit log
        log_audit(
            hospital_id,
            current_user["user_id"],
            "USER_UPDATED",
            "user",
            user_id,
            {
                "updated_fields": list(updates.keys())
            }
        )

        return {
            "message": "User updated successfully",
            "user": updated_user
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()

        logger.exception("User update failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to update user"
        )

    finally:
        if connection:
            connection.close()


class UserStatusUpdate(BaseModel):
    is_active: bool


@router.patch("/{user_id}/status")
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    """Activate or deactivate a user account."""

    if current_user["hospital_id"] != hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot manage another hospital's users"
        )

    if (
        user_id == current_user["user_id"]
        and not data.is_active
    ):
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account"
        )

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                UPDATE users
                SET is_active = %s
                WHERE user_id = %s
                RETURNING
                    user_id,
                    full_name,
                    email,
                    role,
                    is_active,
                    created_at
                """,
                (data.is_active, user_id)
            )

            updated_user = cursor.fetchone()

            if not updated_user:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )

        connection.commit()

        log_audit(
            hospital_id,
            current_user["user_id"],
            "USER_ACTIVATED" if data.is_active else "USER_DEACTIVATED",
            "user",
            user_id,
            {"is_active": data.is_active}
        )

        return {
            "message": (
                "User activated successfully"
                if data.is_active
                else "User deactivated successfully"
            ),
            "user": updated_user
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()

        logger.exception("User status update failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to update user status"
        )

    finally:
        if connection:
            connection.close()
	
