
from datetime import date, time
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from database.hospital_db import get_hospital_connection
from app.core.security import get_current_user


router = APIRouter(
    prefix="/api/appointments",
    tags=["Appointment Management"]
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

AppointmentStatus = Literal[
    "scheduled",
    "completed",
    "cancelled",
    "no_show"
]


class AppointmentCreate(BaseModel):
    patient_id: int = Field(..., gt=0)
    doctor_id: int = Field(..., gt=0)

    appointment_date: date
    appointment_time: time

    reason: Optional[str] = None
    status: AppointmentStatus = "scheduled"


class AppointmentUpdate(BaseModel):
    patient_id: Optional[int] = Field(default=None, gt=0)
    doctor_id: Optional[int] = Field(default=None, gt=0)

    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None

    reason: Optional[str] = None
    status: Optional[AppointmentStatus] = None


# --------------------------------------------------
# CREATE APPOINTMENT
# POST /api/appointments/
# --------------------------------------------------

@router.post("/", status_code=201)
def create_appointment(
    appointment: AppointmentCreate,
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    verify_hospital_access(hospital_id, current_user)

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Check patient exists
            cursor.execute(
                """
                SELECT patient_id
                FROM patients
                WHERE patient_id = %s;
                """,
                (appointment.patient_id,)
            )

            if not cursor.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Patient not found"
                )

            # Check doctor exists
            cursor.execute(
                """
                SELECT doctor_id
                FROM doctors
                WHERE doctor_id = %s;
                """,
                (appointment.doctor_id,)
            )

            if not cursor.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Doctor not found"
                )

            # Insert appointment
            cursor.execute(
                """
                INSERT INTO appointments (
                    patient_id,
                    doctor_id,
                    appointment_date,
                    appointment_time,
                    reason,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING appointment_id;
                """,
                (
                    appointment.patient_id,
                    appointment.doctor_id,
                    appointment.appointment_date,
                    appointment.appointment_time,
                    appointment.reason,
                    appointment.status
                )
            )

            result = cursor.fetchone()

        connection.commit()

        return {
            "message": "Appointment created successfully",
            "hospital_id": hospital_id,
            "appointment_id": result["appointment_id"]
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("CREATE APPOINTMENT ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Failed to create appointment"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET ALL APPOINTMENTS
# GET /api/appointments/
# --------------------------------------------------

@router.get("/")
def get_appointments(
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
                    a.appointment_id,
                    a.patient_id,
                    p.full_name AS patient_name,
                    a.doctor_id,
                    u.full_name AS doctor_name,
                    a.appointment_date,
                    a.appointment_time,
                    a.reason,
                    a.status,
                    a.created_at
                FROM appointments a
                JOIN patients p
                    ON a.patient_id = p.patient_id
                JOIN doctors d
                    ON a.doctor_id = d.doctor_id
                JOIN users u
                    ON d.user_id = u.user_id
                ORDER BY
                    a.appointment_date DESC,
                    a.appointment_time DESC;
                """
            )

            appointments = cursor.fetchall()

        return {
            "hospital_id": hospital_id,
            "total_appointments": len(appointments),
            "appointments": appointments
        }

    except Exception as error:
        print("GET APPOINTMENTS ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Failed to fetch appointments"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET APPOINTMENT BY ID
# GET /api/appointments/{appointment_id}
# --------------------------------------------------

@router.get("/{appointment_id}")
def get_appointment(
    appointment_id: int,
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
                    a.appointment_id,
                    a.patient_id,
                    p.full_name AS patient_name,
                    a.doctor_id,
                    u.full_name AS doctor_name,
                    a.appointment_date,
                    a.appointment_time,
                    a.reason,
                    a.status,
                    a.created_at
                FROM appointments a
                JOIN patients p
                    ON a.patient_id = p.patient_id
                JOIN doctors d
                    ON a.doctor_id = d.doctor_id
                JOIN users u
                    ON d.user_id = u.user_id
                WHERE a.appointment_id = %s;
                """,
                (appointment_id,)
            )

            appointment = cursor.fetchone()

        if not appointment:
            raise HTTPException(
                status_code=404,
                detail="Appointment not found"
            )

        return {
            "hospital_id": hospital_id,
            "appointment": appointment
        }

    except HTTPException:
        raise

    except Exception as error:
        print("GET APPOINTMENT ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Failed to fetch appointment"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# UPDATE APPOINTMENT
# PUT /api/appointments/{appointment_id}
# --------------------------------------------------

@router.put("/{appointment_id}")
def update_appointment(
    appointment_id: int,
    appointment: AppointmentUpdate,
    hospital_id: int = Query(1, ge=1, le=3),
    current_user: dict = Depends(get_current_user)
):
    verify_hospital_access(hospital_id, current_user)

    connection = None

    try:
        update_data = appointment.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )

        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Validate patient_id if supplied
            if "patient_id" in update_data:
                cursor.execute(
                    """
                    SELECT patient_id
                    FROM patients
                    WHERE patient_id = %s;
                    """,
                    (update_data["patient_id"],)
                )

                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail="Patient not found"
                    )

            # Validate doctor_id if supplied
            if "doctor_id" in update_data:
                cursor.execute(
                    """
                    SELECT doctor_id
                    FROM doctors
                    WHERE doctor_id = %s;
                    """,
                    (update_data["doctor_id"],)
                )

                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail="Doctor not found"
                    )

            allowed_columns = {
                "patient_id",
                "doctor_id",
                "appointment_date",
                "appointment_time",
                "reason",
                "status"
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

            values.append(appointment_id)

            cursor.execute(
                f"""
                UPDATE appointments
                SET {set_clause}
                WHERE appointment_id = %s
                RETURNING appointment_id;
                """,
                tuple(values)
            )

            updated_appointment = cursor.fetchone()

        if not updated_appointment:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Appointment not found"
            )

        connection.commit()

        return {
            "message": "Appointment updated successfully",
            "hospital_id": hospital_id,
            "appointment_id": appointment_id
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("UPDATE APPOINTMENT ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Failed to update appointment"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# DELETE APPOINTMENT
# DELETE /api/appointments/{appointment_id}
# --------------------------------------------------

@router.delete("/{appointment_id}")
def delete_appointment(
    appointment_id: int,
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
                DELETE FROM appointments
                WHERE appointment_id = %s
                RETURNING appointment_id;
                """,
                (appointment_id,)
            )

            deleted_appointment = cursor.fetchone()

        if not deleted_appointment:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Appointment not found"
            )

        connection.commit()

        return {
            "message": "Appointment deleted successfully",
            "hospital_id": hospital_id,
            "appointment_id": appointment_id
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("DELETE APPOINTMENT ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Failed to delete appointment"
        )

    finally:
        if connection:
            connection.close()
