
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from database.hospital_db import get_hospital_connection
from app.core.security import get_current_user


router = APIRouter(
    prefix="/api/patients",
    tags=["Patient Management"]
)


# --------------------------------------------------
# AUTHENTICATION + HOSPITAL ACCESS CHECK
# --------------------------------------------------

def verify_hospital_access(
    hospital_id: int,
    current_user: dict
):
    if hospital_id != current_user["hospital_id"]:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another hospital's data"
        )


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class PatientCreate(BaseModel):
    patient_number: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=150)
    date_of_birth: date
    gender: str = Field(..., min_length=1, max_length=20)

    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None

    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class PatientUpdate(BaseModel):
    patient_number: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None

    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None

    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


# --------------------------------------------------
# CREATE PATIENT
# POST /api/patients/
# --------------------------------------------------

@router.post("/", status_code=201)
def create_patient(
    patient: PatientCreate,
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
                INSERT INTO patients (
                    patient_number,
                    full_name,
                    date_of_birth,
                    gender,
                    phone,
                    email,
                    address,
                    blood_group,
                    emergency_contact_name,
                    emergency_contact_phone
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                RETURNING patient_id;
                """,
                (
                    patient.patient_number,
                    patient.full_name,
                    patient.date_of_birth,
                    patient.gender,
                    patient.phone,
                    patient.email,
                    patient.address,
                    patient.blood_group,
                    patient.emergency_contact_name,
                    patient.emergency_contact_phone
                )
            )

            result = cursor.fetchone()

        connection.commit()

        return {
            "message": "Patient created successfully",
            "hospital_id": hospital_id,
            "patient_id": result["patient_id"]
        }

    except Exception as error:
        if connection:
            connection.rollback()

        print("CREATE PATIENT ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET ALL PATIENTS
# GET /api/patients/
# --------------------------------------------------

@router.get("/")
def get_patients(
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
                SELECT *
                FROM patients
                ORDER BY patient_id DESC;
                """
            )

            patients = cursor.fetchall()

        return {
            "hospital_id": hospital_id,
            "total_patients": len(patients),
            "patients": patients
        }

    except Exception as error:
        print("GET PATIENTS ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET PATIENT BY ID
# GET /api/patients/{patient_id}
# --------------------------------------------------

@router.get("/{patient_id}")
def get_patient(
    patient_id: int,
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
                SELECT *
                FROM patients
                WHERE patient_id = %s;
                """,
                (patient_id,)
            )

            patient = cursor.fetchone()

        if not patient:
            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        return {
            "hospital_id": hospital_id,
            "patient": patient
        }

    except HTTPException:
        raise

    except Exception as error:
        print("GET PATIENT ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# UPDATE PATIENT
# PUT /api/patients/{patient_id}
# --------------------------------------------------

@router.put("/{patient_id}")
def update_patient(
    patient_id: int,
    patient: PatientUpdate,
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    verify_hospital_access(hospital_id, current_user)

    connection = None

    try:
        update_data = patient.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )

        allowed_columns = {
            "patient_number",
            "full_name",
            "date_of_birth",
            "gender",
            "phone",
            "email",
            "address",
            "blood_group",
            "emergency_contact_name",
            "emergency_contact_phone"
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

        values.append(patient_id)

        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                f"""
                UPDATE patients
                SET {set_clause}
                WHERE patient_id = %s
                RETURNING *;
                """,
                tuple(values)
            )

            updated_patient = cursor.fetchone()

        if not updated_patient:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        connection.commit()

        return {
            "message": "Patient updated successfully",
            "hospital_id": hospital_id,
            "patient": updated_patient
        }

    except HTTPException:
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("UPDATE PATIENT ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# DELETE PATIENT
# DELETE /api/patients/{patient_id}
# --------------------------------------------------

@router.delete("/{patient_id}")
def delete_patient(
    patient_id: int,
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
                DELETE FROM patients
                WHERE patient_id = %s
                RETURNING patient_id;
                """,
                (patient_id,)
            )

            deleted_patient = cursor.fetchone()

        if not deleted_patient:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        connection.commit()

        return {
            "message": "Patient deleted successfully",
            "hospital_id": hospital_id,
            "patient_id": patient_id
        }

    except HTTPException:
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("DELETE PATIENT ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()
