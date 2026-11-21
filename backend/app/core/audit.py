"""Best-effort audit logging into each hospital's ``audit_logs`` table."""

import logging

from psycopg2.extras import Json

from database.hospital_db import get_hospital_connection

logger = logging.getLogger("fedhealth.audit")


def log_audit(
    hospital_id,
    user_id,
    action,
    entity_type=None,
    entity_id=None,
    details=None
):
    """Write one audit row. Never raises: auditing must not break requests."""
    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_logs (
                    user_id, action, entity_type, entity_id, details
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    action[:100],
                    entity_type,
                    None if entity_id is None else str(entity_id)[:100],
                    Json(details) if details is not None else None
                )
            )

        connection.commit()

    except Exception:
        logger.exception("Failed to write audit log")

        if connection:
            try:
                connection.rollback()
            except Exception:
                pass

    finally:
        if connection:
            connection.close()
