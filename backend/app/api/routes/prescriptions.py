from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from psycopg2.extras import RealDictCursor

from database.hospital_db import get_hospital_connection


router = APIRouter(
    prefix="/api/prescriptions",
    tags=["Prescriptions"]
)


# --------------------------------------------------
# PYDANTIC MODELS
# --------------------------------------------------

class PrescriptionCreate(BaseModel):
    record_id: int
    patient_id: int
    doctor_id: Optional[int] = None

    medicine_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None


class PrescriptionUpdate(BaseModel):
    record_id: Optional[int] = None
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None

    medicine_name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_connection(hospital_id: int = 1):
    return get_hospital_connection(hospital_id)


def validate_patient(cursor, patient_id: int):

    cursor.execute(
        """
        SELECT patient_id
        FROM patients
        WHERE patient_id = %s
        """,
        (patient_id,)
    )

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail=f"Patient with ID {patient_id} not found"
        )


def validate_doctor(cursor, doctor_id: Optional[int]):

    if doctor_id is None:
        return

    cursor.execute(
        """
        SELECT doctor_id
        FROM doctors
        WHERE doctor_id = %s
        """,
        (doctor_id,)
    )

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail=f"Doctor with ID {doctor_id} not found"
        )


def validate_medical_record(cursor, record_id: int):

    cursor.execute(
        """
        SELECT record_id, patient_id, doctor_id
        FROM medical_records
        WHERE record_id = %s
        """,
        (record_id,)
    )

    record = cursor.fetchone()

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Medical record with ID {record_id} not found"
        )

    return record


# --------------------------------------------------
# CREATE PRESCRIPTION
# POST /api/prescriptions/
# --------------------------------------------------

@router.post("/", status_code=201)
def create_prescription(
    prescription: PrescriptionCreate,
    hospital_id: int = Query(default=1)
):

    connection = None

    try:

        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Validate patient
            validate_patient(
                cursor,
                prescription.patient_id
            )

            # Validate doctor if supplied
            validate_doctor(
                cursor,
                prescription.doctor_id
            )

            # Validate medical record
            medical_record = validate_medical_record(
                cursor,
                prescription.record_id
            )

            # Check patient belongs to the medical record
            if medical_record["patient_id"] != prescription.patient_id:
                raise HTTPException(
                    status_code=400,
                    detail="Patient ID does not match the medical record"
                )

            cursor.execute(
                """
                INSERT INTO prescriptions (
                    record_id,
                    patient_id,
                    doctor_id,
                    medicine_name,
                    dosage,
                    frequency,
                    duration,
                    instructions
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING *
                """,
                (
                    prescription.record_id,
                    prescription.patient_id,
                    prescription.doctor_id,
                    prescription.medicine_name,
                    prescription.dosage,
                    prescription.frequency,
                    prescription.duration,
                    prescription.instructions
                )
            )

            new_prescription = cursor.fetchone()

        connection.commit()

        return {
            "message": "Prescription created successfully",
            "prescription": new_prescription
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:

        if connection:
            connection.rollback()

        print("CREATE PRESCRIPTION ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to create prescription"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET ALL PRESCRIPTIONS
# GET /api/prescriptions/
# --------------------------------------------------

@router.get("/")
def get_all_prescriptions(
    hospital_id: int = Query(default=1)
):

    connection = None

    try:

        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                SELECT
                    pr.*,
                    p.full_name AS patient_name,
                    u.full_name AS doctor_name
                FROM prescriptions pr
                JOIN patients p
                    ON pr.patient_id = p.patient_id
                LEFT JOIN doctors d
                    ON pr.doctor_id = d.doctor_id
                LEFT JOIN users u
                    ON d.user_id = u.user_id
                ORDER BY pr.prescribed_at DESC
                """
            )

            prescriptions = cursor.fetchall()

        return {
            "total_prescriptions": len(prescriptions),
            "prescriptions": prescriptions
        }

    except Exception as error:

        print("GET PRESCRIPTIONS ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch prescriptions"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET PRESCRIPTION BY ID
# GET /api/prescriptions/{prescription_id}
# --------------------------------------------------

@router.get("/{prescription_id}")
def get_prescription(
    prescription_id: int,
    hospital_id: int = Query(default=1)
):

    connection = None

    try:

        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                SELECT
                    pr.*,
                    p.full_name AS patient_name,
                    u.full_name AS doctor_name
                FROM prescriptions pr
                JOIN patients p
                    ON pr.patient_id = p.patient_id
                LEFT JOIN doctors d
                    ON pr.doctor_id = d.doctor_id
                LEFT JOIN users u
                    ON d.user_id = u.user_id
                WHERE pr.prescription_id = %s
                """,
                (prescription_id,)
            )

            prescription = cursor.fetchone()

        if prescription is None:
            raise HTTPException(
                status_code=404,
                detail="Prescription not found"
            )

        return prescription

    except HTTPException:
        raise

    except Exception as error:

        print("GET PRESCRIPTION ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch prescription"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET PRESCRIPTIONS BY PATIENT
# GET /api/prescriptions/patient/{patient_id}
# --------------------------------------------------

@router.get("/patient/{patient_id}")
def get_patient_prescriptions(
    patient_id: int,
    hospital_id: int = Query(default=1)
):

    connection = None

    try:

        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            validate_patient(
                cursor,
                patient_id
            )

            cursor.execute(
                """
                SELECT
                    pr.*,
                    p.full_name AS patient_name,
                    u.full_name AS doctor_name
                FROM prescriptions pr
                JOIN patients p
                    ON pr.patient_id = p.patient_id
                LEFT JOIN doctors d
                    ON pr.doctor_id = d.doctor_id
                LEFT JOIN users u
                    ON d.user_id = u.user_id
                WHERE pr.patient_id = %s
                ORDER BY pr.prescribed_at DESC
                """,
                (patient_id,)
            )

            prescriptions = cursor.fetchall()

        return {
            "patient_id": patient_id,
            "total_prescriptions": len(prescriptions),
            "prescriptions": prescriptions
        }

    except HTTPException:
        raise

    except Exception as error:

        print("PATIENT PRESCRIPTIONS ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch patient prescriptions"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# UPDATE PRESCRIPTION
# PUT /api/prescriptions/{prescription_id}
# --------------------------------------------------

@router.put("/{prescription_id}")
def update_prescription(
    prescription_id: int,
    prescription: PrescriptionUpdate,
    hospital_id: int = Query(default=1)
):

    connection = None

    try:

        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                SELECT prescription_id
                FROM prescriptions
                WHERE prescription_id = %s
                """,
                (prescription_id,)
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Prescription not found"
                )

            update_data = prescription.model_dump(
                exclude_unset=True
            )

            if not update_data:
                raise HTTPException(
                    status_code=400,
                    detail="No fields provided for update"
                )

            # Validate patient if being changed
            if "patient_id" in update_data:
                if update_data["patient_id"] is not None:
                    validate_patient(
                        cursor,
                        update_data["patient_id"]
                    )

            # Validate doctor if being changed
            if "doctor_id" in update_data:
                validate_doctor(
                    cursor,
                    update_data["doctor_id"]
                )

            # Validate medical record if being changed
            if "record_id" in update_data:

                if update_data["record_id"] is not None:

                    medical_record = validate_medical_record(
                        cursor,
                        update_data["record_id"]
                    )

                    # Ensure patient matches record
                    patient_id = update_data.get("patient_id")

                    if patient_id is None:

                        cursor.execute(
                            """
                            SELECT patient_id
                            FROM prescriptions
                            WHERE prescription_id = %s
                            """,
                            (prescription_id,)
                        )

                        current_prescription = cursor.fetchone()

                        patient_id = current_prescription["patient_id"]

                    if medical_record["patient_id"] != patient_id:
                        raise HTTPException(
                            status_code=400,
                            detail="Patient ID does not match the medical record"
                        )

            allowed_columns = {
                "record_id",
                "patient_id",
                "doctor_id",
                "medicine_name",
                "dosage",
                "frequency",
                "duration",
                "instructions"
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
                    detail="No valid fields provided"
                )

            values.append(prescription_id)

            query = f"""
                UPDATE prescriptions
                SET {", ".join(fields)}
                WHERE prescription_id = %s
                RETURNING *
            """

            cursor.execute(
                query,
                tuple(values)
            )

            updated_prescription = cursor.fetchone()

        connection.commit()

        return {
            "message": "Prescription updated successfully",
            "prescription": updated_prescription
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:

        if connection:
            connection.rollback()

        print("UPDATE PRESCRIPTION ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to update prescription"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# DELETE PRESCRIPTION
# DELETE /api/prescriptions/{prescription_id}
# --------------------------------------------------

@router.delete("/{prescription_id}")
def delete_prescription(
    prescription_id: int,
    hospital_id: int = Query(default=1)
):

    connection = None

    try:

        connection = get_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                """
                DELETE FROM prescriptions
                WHERE prescription_id = %s
                RETURNING prescription_id
                """,
                (prescription_id,)
            )

            deleted_prescription = cursor.fetchone()

        if deleted_prescription is None:
            raise HTTPException(
                status_code=404,
                detail="Prescription not found"
            )

        connection.commit()

        return {
            "message": "Prescription deleted successfully",
            "prescription_id": deleted_prescription["prescription_id"]
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:

        if connection:
            connection.rollback()

        print("DELETE PRESCRIPTION ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Unable to delete prescription"
        )

    finally:
        if connection:
            connection.close()