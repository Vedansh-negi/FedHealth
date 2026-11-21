from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

from psycopg2.extras import RealDictCursor

from database.hospital_db import get_hospital_connection


router = APIRouter(
    prefix="/api/medical-records",
    tags=["Medical Records"]
)


# ---------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------

class MedicalRecordCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int] = None

    diagnosis: Optional[str] = None
    clinical_notes: Optional[str] = None

    blood_pressure: Optional[str] = None
    heart_rate: Optional[int] = Field(default=None, ge=0)
    temperature: Optional[float] = None
    oxygen_saturation: Optional[float] = Field(default=None, ge=0, le=100)

    height_cm: Optional[float] = Field(default=None, gt=0)
    weight_kg: Optional[float] = Field(default=None, gt=0)


class MedicalRecordUpdate(BaseModel):
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None
    appointment_id: Optional[int] = None

    diagnosis: Optional[str] = None
    clinical_notes: Optional[str] = None

    blood_pressure: Optional[str] = None
    heart_rate: Optional[int] = Field(default=None, ge=0)
    temperature: Optional[float] = None
    oxygen_saturation: Optional[float] = Field(default=None, ge=0, le=100)

    height_cm: Optional[float] = Field(default=None, gt=0)
    weight_kg: Optional[float] = Field(default=None, gt=0)


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def get_connection(hospital_id: int = 1):
    """
    Gets a database connection for the selected hospital.
    Uses the existing FedHealth hospital database helper.
    """
    return get_hospital_connection(hospital_id)


def validate_patient(cursor, patient_id: int):
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = %s",
        (patient_id,)
    )

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail=f"Patient with ID {patient_id} not found"
        )


def validate_doctor(cursor, doctor_id: int):
    cursor.execute(
        "SELECT doctor_id FROM doctors WHERE doctor_id = %s",
        (doctor_id,)
    )

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail=f"Doctor with ID {doctor_id} not found"
        )


def validate_appointment(cursor, appointment_id: Optional[int]):
    if appointment_id is None:
        return

    cursor.execute(
        """
        SELECT appointment_id
        FROM appointments
        WHERE appointment_id = %s
        """,
        (appointment_id,)
    )

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail=f"Appointment with ID {appointment_id} not found"
        )


# ---------------------------------------------------------
# CREATE MEDICAL RECORD
# POST /api/medical-records/
# ---------------------------------------------------------

@router.post("/", status_code=201)
def create_medical_record(
    record: MedicalRecordCreate,
    hospital_id: int = Query(default=1)
):
    connection = None

    try:
        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Validate patient
            validate_patient(cursor, record.patient_id)

            # Validate doctor
            validate_doctor(cursor, record.doctor_id)

            # Validate appointment if supplied
            validate_appointment(cursor, record.appointment_id)

            cursor.execute(
                """
                INSERT INTO medical_records (
                    patient_id,
                    doctor_id,
                    appointment_id,
                    diagnosis,
                    clinical_notes,
                    blood_pressure,
                    heart_rate,
                    temperature,
                    oxygen_saturation,
                    height_cm,
                    weight_kg
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING *
                """,
                (
                    record.patient_id,
                    record.doctor_id,
                    record.appointment_id,
                    record.diagnosis,
                    record.clinical_notes,
                    record.blood_pressure,
                    record.heart_rate,
                    record.temperature,
                    record.oxygen_saturation,
                    record.height_cm,
                    record.weight_kg
                )
            )

            new_record = cursor.fetchone()

        connection.commit()

        return {
            "message": "Medical record created successfully",
            "medical_record": new_record
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Error creating medical record: {str(e)}"
        )

    finally:
        if connection:
            connection.close()


# ---------------------------------------------------------
# GET ALL MEDICAL RECORDS
# GET /api/medical-records/
# ---------------------------------------------------------

@router.get("/")
def get_all_medical_records(
    hospital_id: int = Query(default=1)
):
    connection = None

    try:
        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                SELECT
                    mr.*,
                    p.full_name AS patient_name,
                    d.doctor_id,
                    u.full_name AS doctor_name
                FROM medical_records mr
                JOIN patients p
                    ON mr.patient_id = p.patient_id
                JOIN doctors d
                    ON mr.doctor_id = d.doctor_id
                JOIN users u
                    ON d.user_id = u.user_id
                ORDER BY mr.recorded_at DESC
                """
            )

            records = cursor.fetchall()

        return {
            "total_records": len(records),
            "medical_records": records
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching medical records: {str(e)}"
        )

    finally:
        if connection:
            connection.close()


# ---------------------------------------------------------
# GET MEDICAL RECORD BY ID
# GET /api/medical-records/{record_id}
# ---------------------------------------------------------

@router.get("/{record_id}")
def get_medical_record(
    record_id: int,
    hospital_id: int = Query(default=1)
):
    connection = None

    try:
        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                SELECT
                    mr.*,
                    p.full_name AS patient_name,
                    d.doctor_id,
                    u.full_name AS doctor_name
                FROM medical_records mr
                JOIN patients p
                    ON mr.patient_id = p.patient_id
                JOIN doctors d
                    ON mr.doctor_id = d.doctor_id
                JOIN users u
                    ON d.user_id = u.user_id
                WHERE mr.record_id = %s
                """,
                (record_id,)
            )

            record = cursor.fetchone()

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="Medical record not found"
            )

        return record

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching medical record: {str(e)}"
        )

    finally:
        if connection:
            connection.close()


# ---------------------------------------------------------
# GET PATIENT MEDICAL HISTORY
# GET /api/medical-records/patient/{patient_id}
# ---------------------------------------------------------

@router.get("/patient/{patient_id}")
def get_patient_medical_history(
    patient_id: int,
    hospital_id: int = Query(default=1)
):
    connection = None

    try:
        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            validate_patient(cursor, patient_id)

            cursor.execute(
                """
                SELECT
                    mr.*,
                    p.full_name AS patient_name,
                    u.full_name AS doctor_name,
                    d.specialization
                FROM medical_records mr
                JOIN patients p
                    ON mr.patient_id = p.patient_id
                JOIN doctors d
                    ON mr.doctor_id = d.doctor_id
                JOIN users u
                    ON d.user_id = u.user_id
                WHERE mr.patient_id = %s
                ORDER BY mr.recorded_at DESC
                """,
                (patient_id,)
            )

            records = cursor.fetchall()

        return {
            "patient_id": patient_id,
            "total_records": len(records),
            "medical_history": records
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching patient medical history: {str(e)}"
        )

    finally:
        if connection:
            connection.close()


# ---------------------------------------------------------
# UPDATE MEDICAL RECORD
# PUT /api/medical-records/{record_id}
# ---------------------------------------------------------

@router.put("/{record_id}")
def update_medical_record(
    record_id: int,
    record: MedicalRecordUpdate,
    hospital_id: int = Query(default=1)
):
    connection = None

    try:
        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                SELECT record_id
                FROM medical_records
                WHERE record_id = %s
                """,
                (record_id,)
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Medical record not found"
                )

            update_data = record.model_dump(exclude_unset=True)

            if not update_data:
                raise HTTPException(
                    status_code=400,
                    detail="No fields provided for update"
                )

            if "patient_id" in update_data:
                if update_data["patient_id"] is not None:
                    validate_patient(cursor, update_data["patient_id"])

            if "doctor_id" in update_data:
                if update_data["doctor_id"] is not None:
                    validate_doctor(cursor, update_data["doctor_id"])

            if "appointment_id" in update_data:
                validate_appointment(
                    cursor,
                    update_data["appointment_id"]
                )

            allowed_columns = {
                "patient_id",
                "doctor_id",
                "appointment_id",
                "diagnosis",
                "clinical_notes",
                "blood_pressure",
                "heart_rate",
                "temperature",
                "oxygen_saturation",
                "height_cm",
                "weight_kg"
            }

            fields = []
            values = []

            for column, value in update_data.items():

                if column not in allowed_columns:
                    continue

                fields.append(f"{column} = %s")
                values.append(value)

            if not fields:
                raise HTTPException(
                    status_code=400,
                    detail="No valid fields provided for update"
                )

            values.append(record_id)

            query = f"""
                UPDATE medical_records
                SET {", ".join(fields)}
                WHERE record_id = %s
                RETURNING *
            """

            cursor.execute(query, tuple(values))
            updated_record = cursor.fetchone()

        connection.commit()

        return {
            "message": "Medical record updated successfully",
            "medical_record": updated_record
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Error updating medical record: {str(e)}"
        )

    finally:
        if connection:
            connection.close()


# ---------------------------------------------------------
# DELETE MEDICAL RECORD
# DELETE /api/medical-records/{record_id}
# ---------------------------------------------------------

@router.delete("/{record_id}")
def delete_medical_record(
    record_id: int,
    hospital_id: int = Query(default=1)
):
    connection = None

    try:
        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                DELETE FROM medical_records
                WHERE record_id = %s
                RETURNING record_id
                """,
                (record_id,)
            )

            deleted_record = cursor.fetchone()

        if deleted_record is None:
            raise HTTPException(
                status_code=404,
                detail="Medical record not found"
            )

        connection.commit()

        return {
            "message": "Medical record deleted successfully",
            "record_id": deleted_record["record_id"]
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as e:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Error deleting medical record: {str(e)}"
        )

    finally:
        if connection:
            connection.close()