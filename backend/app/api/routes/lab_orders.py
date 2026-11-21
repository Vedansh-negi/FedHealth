from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from database.hospital_db import get_hospital_connection


router = APIRouter(
    prefix="/api/lab-orders",
    tags=["Lab Orders"]
)


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class LabOrderCreate(BaseModel):
    patient_id: int
    doctor_id: Optional[int] = None

    test_name: str = Field(
        ...,
        min_length=1,
        max_length=150
    )

    priority: Optional[str] = "Normal"
    status: Optional[str] = "Pending"


class LabOrderUpdate(BaseModel):
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None
    test_name: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


# --------------------------------------------------
# CREATE LAB ORDER
# POST /api/lab-orders/
# --------------------------------------------------

@router.post("/", status_code=201)
def create_lab_order(
    order: LabOrderCreate,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Validate patient
            cursor.execute(
                """
                SELECT patient_id
                FROM patients
                WHERE patient_id = %s;
                """,
                (order.patient_id,)
            )

            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Patient not found"
                )

            # Validate doctor if provided
            if order.doctor_id is not None:
                cursor.execute(
                    """
                    SELECT doctor_id
                    FROM doctors
                    WHERE doctor_id = %s;
                    """,
                    (order.doctor_id,)
                )

                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=404,
                        detail="Doctor not found"
                    )

            # Insert lab order
            cursor.execute(
                """
                INSERT INTO lab_orders (
                    patient_id,
                    doctor_id,
                    test_name,
                    priority,
                    status,
                    ordered_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING lab_order_id;
                """,
                (
                    order.patient_id,
                    order.doctor_id,
                    order.test_name,
                    order.priority,
                    order.status,
                    datetime.now()
                )
            )

            result = cursor.fetchone()

        connection.commit()

        return {
            "message": "Lab order created successfully",
            "hospital_id": hospital_id,
            "lab_order_id": result["lab_order_id"]
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("CREATE LAB ORDER ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET ALL LAB ORDERS
# GET /api/lab-orders/
# --------------------------------------------------

@router.get("/")
def get_lab_orders(
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    lo.lab_order_id,
                    lo.patient_id,
                    p.full_name AS patient_name,
                    lo.doctor_id,
                    u.full_name AS doctor_name,
                    lo.test_name,
                    lo.priority,
                    lo.status,
                    lo.ordered_at
                FROM lab_orders lo
                JOIN patients p
                    ON lo.patient_id = p.patient_id
                LEFT JOIN doctors d
                    ON lo.doctor_id = d.doctor_id
                LEFT JOIN users u
                    ON d.user_id = u.user_id
                ORDER BY lo.ordered_at DESC;
                """
            )

            lab_orders = cursor.fetchall()

        return {
            "hospital_id": hospital_id,
            "total_lab_orders": len(lab_orders),
            "lab_orders": lab_orders
        }

    except Exception as error:
        print("GET LAB ORDERS ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET LAB ORDER BY ID
# GET /api/lab-orders/{order_id}
# --------------------------------------------------

@router.get("/{order_id}")
def get_lab_order(
    order_id: int,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    lab_order_id,
                    patient_id,
                    doctor_id,
                    test_name,
                    priority,
                    status,
                    ordered_at
                FROM lab_orders
                WHERE lab_order_id = %s;
                """,
                (order_id,)
            )

            lab_order = cursor.fetchone()

        if not lab_order:
            raise HTTPException(
                status_code=404,
                detail="Lab order not found"
            )

        return {
            "hospital_id": hospital_id,
            "lab_order": lab_order
        }

    except HTTPException:
        raise

    except Exception as error:
        print("GET LAB ORDER ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# UPDATE LAB ORDER
# PUT /api/lab-orders/{order_id}
# --------------------------------------------------

@router.put("/{order_id}")
def update_lab_order(
    order_id: int,
    order: LabOrderUpdate,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = None

    try:
        update_data = order.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )

        allowed_columns = {
            "patient_id",
            "doctor_id",
            "test_name",
            "priority",
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

        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Verify lab order exists
            cursor.execute(
                """
                SELECT lab_order_id
                FROM lab_orders
                WHERE lab_order_id = %s;
                """,
                (order_id,)
            )

            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Lab order not found"
                )

            # Validate updated patient
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
                        status_code=404,
                        detail="Patient not found"
                    )

            # Validate updated doctor
            if (
                "doctor_id" in update_data
                and update_data["doctor_id"] is not None
            ):
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
                        status_code=404,
                        detail="Doctor not found"
                    )

            set_clause = ", ".join(
                f"{column} = %s"
                for column in columns
            )

            values = [
                update_data[column]
                for column in columns
            ]

            values.append(order_id)

            cursor.execute(
                f"""
                UPDATE lab_orders
                SET {set_clause}
                WHERE lab_order_id = %s
                RETURNING *;
                """,
                tuple(values)
            )

            updated_order = cursor.fetchone()

        connection.commit()

        return {
            "message": "Lab order updated successfully",
            "hospital_id": hospital_id,
            "lab_order": updated_order
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("UPDATE LAB ORDER ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# DELETE LAB ORDER
# DELETE /api/lab-orders/{order_id}
# --------------------------------------------------

@router.delete("/{order_id}")
def delete_lab_order(
    order_id: int,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                DELETE FROM lab_orders
                WHERE lab_order_id = %s
                RETURNING lab_order_id;
                """,
                (order_id,)
            )

            deleted_order = cursor.fetchone()

        if not deleted_order:
            raise HTTPException(
                status_code=404,
                detail="Lab order not found"
            )

        connection.commit()

        return {
            "message": "Lab order deleted successfully",
            "hospital_id": hospital_id,
            "lab_order_id": order_id
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        print("DELETE LAB ORDER ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()


# --------------------------------------------------
# GET LAB ORDERS BY PATIENT
# GET /api/lab-orders/patient/{patient_id}
# --------------------------------------------------

@router.get("/patient/{patient_id}")
def get_patient_lab_orders(
    patient_id: int,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Verify patient exists
            cursor.execute(
                """
                SELECT patient_id
                FROM patients
                WHERE patient_id = %s;
                """,
                (patient_id,)
            )

            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Patient not found"
                )

            cursor.execute(
                """
                SELECT
                    lab_order_id,
                    patient_id,
                    doctor_id,
                    test_name,
                    priority,
                    status,
                    ordered_at
                FROM lab_orders
                WHERE patient_id = %s
                ORDER BY ordered_at DESC;
                """,
                (patient_id,)
            )

            lab_orders = cursor.fetchall()

        return {
            "hospital_id": hospital_id,
            "patient_id": patient_id,
            "total_lab_orders": len(lab_orders),
            "lab_orders": lab_orders
        }

    except HTTPException:
        raise

    except Exception as error:
        print("GET PATIENT LAB ORDERS ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    finally:
        if connection:
            connection.close()