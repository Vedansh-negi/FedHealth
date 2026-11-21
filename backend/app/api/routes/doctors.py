
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field, EmailStr
from psycopg2.extras import RealDictCursor

from database.hospital_db import get_hospital_connection
from app.core.security import get_current_user, hash_password


router = APIRouter(
    prefix="/api/doctors",
    tags=["Doctor Management"]
)


# --------------------------------------------------
# HOSPITAL ACCESS VERIFICATION
# --------------------------------------------------

def verify_hospital_access(
    hospital_id: int,
    current_user: dict
):
    if current_user["hospital_id"] != hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this hospital"
        )


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class DoctorCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)

    department_id: int = Field(..., gt=0)
    specialization: str = Field(..., min_length=1, max_length=100)
    qualification: str = Field(..., min_length=1, max_length=100)
    license_number: str = Field(..., min_length=1, max_length=100)

    consultation_fee: float = Field(..., ge=0)


class DoctorUpdate(BaseModel):
    department_id: Optional[int] = Field(default=None, gt=0)

    specialization: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    qualification: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    license_number: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    consultation_fee: Optional[float] = Field(
        default=None,
        ge=0
    )


# --------------------------------------------------
# GET DEPARTMENTS
# GET /api/doctors/departments
# --------------------------------------------------

@router.get("/departments")
def get_departments(
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    verify_hospital_access(hospital_id, current_user)

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    department_id,
                    department_name
                FROM departments
                ORDER BY department_name;
                """
            )

            departments = cursor.fetchall()

        return {
            "hospital_id": hospital_id,
            "departments": departments
        }

    except Exception as error:
        print("GET DEPARTMENTS ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch departments"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# CREATE DOCTOR
# POST /api/doctors/
# --------------------------------------------------

@router.post("/", status_code=201)
def create_doctor(
    doctor: DoctorCreate,
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    verify_hospital_access(hospital_id, current_user)

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Check if email already exists
            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE LOWER(email) = LOWER(%s);
                """,
                (str(doctor.email).strip(),)
            )

            if cursor.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail="Email already registered"
                )

            # Verify department exists
            cursor.execute(
                """
                SELECT department_id
                FROM departments
                WHERE department_id = %s;
                """,
                (doctor.department_id,)
            )

            if not cursor.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Department not found"
                )

            # Create user account
            cursor.execute(
                """
                INSERT INTO users (
                    full_name,
                    email,
                    password_hash,
                    role,
                    is_active
                )
                VALUES (%s, %s, %s, 'doctor', TRUE)
                RETURNING user_id;
                """,
                (
                    doctor.full_name.strip(),
                    str(doctor.email).strip().lower(),
                    hash_password(doctor.password)
                )
            )

            user = cursor.fetchone()
            user_id = user["user_id"]

            # Create professional doctor record
            cursor.execute(
                """
                INSERT INTO doctors (
                    user_id,
                    department_id,
                    specialization,
                    qualification,
                    license_number,
                    consultation_fee
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING doctor_id;
                """,
                (
                    user_id,
                    doctor.department_id,
                    doctor.specialization.strip(),
                    doctor.qualification.strip(),
                    doctor.license_number.strip(),
                    doctor.consultation_fee
                )
            )

            result = cursor.fetchone()

        connection.commit()

        return {
            "message": "Doctor created successfully",
            "hospital_id": hospital_id,
            "doctor_id": result["doctor_id"],
            "user_id": user_id
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("CREATE DOCTOR ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to create doctor"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET ALL DOCTORS
# GET /api/doctors/
# --------------------------------------------------

@router.get("/")
def get_doctors(
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    verify_hospital_access(hospital_id, current_user)

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    d.doctor_id,
                    d.user_id,
                    u.full_name,
                    u.email,
                    d.department_id,
                    dep.department_name,
                    d.specialization,
                    d.qualification,
                    d.license_number,
                    d.consultation_fee
                FROM doctors d
                JOIN users u
                    ON d.user_id = u.user_id
                JOIN departments dep
                    ON d.department_id = dep.department_id
                ORDER BY d.doctor_id DESC;
                """
            )

            doctors = cursor.fetchall()

        return {
            "hospital_id": hospital_id,
            "total_doctors": len(doctors),
            "doctors": doctors
        }

    except Exception as error:
        print("GET DOCTORS ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch doctors"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET DOCTOR BY ID
# GET /api/doctors/{doctor_id}
# --------------------------------------------------

@router.get("/{doctor_id}")
def get_doctor(
    doctor_id: int,
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    verify_hospital_access(hospital_id, current_user)

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    d.doctor_id,
                    d.user_id,
                    u.full_name,
                    u.email,
                    d.department_id,
                    dep.department_name,
                    d.specialization,
                    d.qualification,
                    d.license_number,
                    d.consultation_fee
                FROM doctors d
                JOIN users u
                    ON d.user_id = u.user_id
                JOIN departments dep
                    ON d.department_id = dep.department_id
                WHERE d.doctor_id = %s;
                """,
                (doctor_id,)
            )

            doctor = cursor.fetchone()

        if not doctor:
            raise HTTPException(
                status_code=404,
                detail="Doctor not found"
            )

        return {
            "hospital_id": hospital_id,
            "doctor": doctor
        }

    except HTTPException:
        raise

    except Exception as error:
        print("GET DOCTOR ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch doctor"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# UPDATE DOCTOR
# PUT /api/doctors/{doctor_id}
# --------------------------------------------------

@router.put("/{doctor_id}")
def update_doctor(
    doctor_id: int,
    doctor: DoctorUpdate,
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    verify_hospital_access(hospital_id, current_user)

    connection = None

    try:
        update_data = doctor.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )

        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Validate department if supplied
            if "department_id" in update_data:
                cursor.execute(
                    """
                    SELECT department_id
                    FROM departments
                    WHERE department_id = %s;
                    """,
                    (update_data["department_id"],)
                )

                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail="Department not found"
                    )

            allowed_columns = {
                "department_id",
                "specialization",
                "qualification",
                "license_number",
                "consultation_fee"
            }

            columns = [
                column
                for column in update_data
                if column in allowed_columns
            ]

            if not columns:
                raise HTTPException(
                    status_code=400,
                    detail="No valid fields provided"
                )

            set_clause = ", ".join(
                f"{column} = %s"
                for column in columns
            )

            values = [
                update_data[column]
                for column in columns
            ]

            values.append(doctor_id)

            cursor.execute(
                f"""
                UPDATE doctors
                SET {set_clause}
                WHERE doctor_id = %s
                RETURNING doctor_id;
                """,
                tuple(values)
            )

            updated_doctor = cursor.fetchone()

        if not updated_doctor:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Doctor not found"
            )

        connection.commit()

        return {
            "message": "Doctor updated successfully",
            "hospital_id": hospital_id,
            "doctor_id": doctor_id
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("UPDATE DOCTOR ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to update doctor"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# DELETE DOCTOR
# DELETE /api/doctors/{doctor_id}
# --------------------------------------------------

@router.delete("/{doctor_id}")
def delete_doctor(
    doctor_id: int,
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    verify_hospital_access(hospital_id, current_user)

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                DELETE FROM doctors
                WHERE doctor_id = %s
                RETURNING doctor_id;
                """,
                (doctor_id,)
            )

            deleted_doctor = cursor.fetchone()

        if not deleted_doctor:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Doctor not found"
            )

        connection.commit()

        return {
            "message": "Doctor deleted successfully",
            "hospital_id": hospital_id,
            "doctor_id": doctor_id
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("DELETE DOCTOR ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to delete doctor"
        )

    finally:
        if connection:
            connection.close()
