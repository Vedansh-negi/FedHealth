import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.core.security import ADMIN, require_roles
from database.hospital_db import get_hospital_connection


logger = logging.getLogger("fedhealth.audit")

router = APIRouter(
    prefix="/api/audit-logs",
    tags=["Audit Logs"]
)


@router.get("")
@router.get("/", include_in_schema=False)
def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    action: str = Query(None, max_length=100),
    current_user: dict = Depends(require_roles(ADMIN))
):
    """Audit trail of the admin's own hospital."""
    hospital_id = current_user["hospital_id"]
    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    a.audit_id,
                    a.user_id,
                    u.full_name,
                    u.role,
                    a.action,
                    a.entity_type,
                    a.entity_id,
                    a.details,
                    a.created_at
                FROM audit_logs a
                LEFT JOIN users u ON u.user_id = a.user_id
                WHERE (%s IS NULL OR a.action = %s)
                ORDER BY a.audit_id DESC
                LIMIT %s
                """,
                (action, action, limit)
            )

            logs = cursor.fetchall()

        return {
            "hospital_id": hospital_id,
            "total_logs": len(logs),
            "logs": logs
        }

    except Exception:
        logger.exception("Reading audit logs failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch audit logs"
        )

    finally:
        if connection:
            connection.close()
