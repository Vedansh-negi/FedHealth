
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from database.hospital_db import get_hospital_connection


router = APIRouter(
    prefix="/api/lab-reports",
    tags=["Lab Reports"]
)


class LabReportCreate(BaseModel):
    lab_order_id: int
    result_value: str
    result_unit: Optional[str] = None
    reference_range: Optional[str] = None
    remarks: Optional[str] = None
    reported_by: Optional[int] = None


class LabReportUpdate(BaseModel):
    result_value: Optional[str] = None
    result_unit: Optional[str] = None
    reference_range: Optional[str] = None
    remarks: Optional[str] = None
    reported_by: Optional[int] = None


# CREATE LAB REPORT
@router.post("/")
def create_lab_report(
    report: LabReportCreate,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = get_hospital_connection(hospital_id)

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT lab_order_id
            FROM lab_orders
            WHERE lab_order_id = %s
            """,
            (report.lab_order_id,)
        )

        if not cursor.fetchone():
            raise HTTPException(
                status_code=404,
                detail="Lab order not found"
            )

        cursor.execute(
            """
            INSERT INTO lab_reports (
                lab_order_id,
                result_value,
                result_unit,
                reference_range,
                remarks,
                reported_by,
                reported_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING *
            """,
            (
                report.lab_order_id,
                report.result_value,
                report.result_unit,
                report.reference_range,
                report.remarks,
                report.reported_by
            )
        )

        new_report = cursor.fetchone()
        connection.commit()

        return {
            "message": "Lab report created successfully",
            "hospital_id": hospital_id,
            "report": dict(new_report)
        }

    except HTTPException:
        raise

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        connection.close()


# GET ALL LAB REPORTS
@router.get("/")
def get_lab_reports(
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = get_hospital_connection(hospital_id)

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT
                lr.*,
                lo.patient_id,
                lo.test_name
            FROM lab_reports lr
            JOIN lab_orders lo
                ON lr.lab_order_id = lo.lab_order_id
            ORDER BY lr.reported_at DESC
            """
        )

        reports = cursor.fetchall()

        return {
            "hospital_id": hospital_id,
            "total": len(reports),
            "reports": [dict(report) for report in reports]
        }

    finally:
        connection.close()


# GET LAB REPORT BY ID
@router.get("/{report_id}")
def get_lab_report(
    report_id: int,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = get_hospital_connection(hospital_id)

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT
                lr.*,
                lo.patient_id,
                lo.test_name
            FROM lab_reports lr
            JOIN lab_orders lo
                ON lr.lab_order_id = lo.lab_order_id
            WHERE lr.lab_report_id = %s
            """,
            (report_id,)
        )

        report = cursor.fetchone()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Lab report not found"
            )

        return dict(report)

    finally:
        connection.close()


# GET REPORTS BY PATIENT
@router.get("/patient/{patient_id}")
def get_patient_lab_reports(
    patient_id: int,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = get_hospital_connection(hospital_id)

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT
                lr.*,
                lo.patient_id,
                lo.test_name
            FROM lab_reports lr
            JOIN lab_orders lo
                ON lr.lab_order_id = lo.lab_order_id
            WHERE lo.patient_id = %s
            ORDER BY lr.reported_at DESC
            """,
            (patient_id,)
        )

        reports = cursor.fetchall()

        return {
            "patient_id": patient_id,
            "hospital_id": hospital_id,
            "total": len(reports),
            "reports": [dict(report) for report in reports]
        }

    finally:
        connection.close()


# UPDATE LAB REPORT
@router.put("/{report_id}")
def update_lab_report(
    report_id: int,
    report: LabReportUpdate,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = get_hospital_connection(hospital_id)

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        update_data = report.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )

        set_clause = ", ".join(
            f"{column} = %s"
            for column in update_data
        )

        values = list(update_data.values())
        values.append(report_id)

        cursor.execute(
            f"""
            UPDATE lab_reports
            SET {set_clause}
            WHERE lab_report_id = %s
            RETURNING *
            """,
            values
        )

        updated_report = cursor.fetchone()

        if not updated_report:
            raise HTTPException(
                status_code=404,
                detail="Lab report not found"
            )

        connection.commit()

        return {
            "message": "Lab report updated successfully",
            "report": dict(updated_report)
        }

    except HTTPException:
        raise

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        connection.close()


# DELETE LAB REPORT
@router.delete("/{report_id}")
def delete_lab_report(
    report_id: int,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = get_hospital_connection(hospital_id)

    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            DELETE FROM lab_reports
            WHERE lab_report_id = %s
            RETURNING lab_report_id
            """,
            (report_id,)
        )

        deleted_report = cursor.fetchone()

        if not deleted_report:
            raise HTTPException(
                status_code=404,
                detail="Lab report not found"
            )

        connection.commit()

        return {
            "message": "Lab report deleted successfully",
            "lab_report_id": deleted_report["lab_report_id"]
        }

    except HTTPException:
        raise

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        connection.close()
