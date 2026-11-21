import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.core.security import ADMIN, require_roles
from database.federated_db import get_federated_connection
from os_layer.resource_monitor import get_resource_usage, save_resource_usage


logger = logging.getLogger("fedhealth.os")

router = APIRouter(
    prefix="/api/os",
    tags=["OS Monitoring"],
    dependencies=[Depends(require_roles(ADMIN))]
)


@router.get("/metrics")
def os_metrics():
    try:
        usage = get_resource_usage()
    except Exception:
        logger.exception("Reading resource usage failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch OS monitoring data"
        )

    # The snapshot is also stored for the history view; if the database is
    # down the live numbers are still returned.
    try:
        save_resource_usage(usage)
    except Exception:
        logger.exception("Saving resource snapshot failed")

    return {
        "cpu_percent": usage["cpu_percent"],
        "memory_percent": usage["memory_percent"],
        "system_memory_used_mb": usage["system_memory_used_mb"],
        "process_memory_mb": usage["process_memory_mb"],
        "available_memory_mb": usage["available_memory_mb"]
    }


@router.get("/history")
def os_history(limit: int = Query(20, ge=1, le=500)):
    connection = None

    try:
        connection = get_federated_connection()

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    snapshot_id,
                    cpu_percent,
                    memory_percent,
                    system_memory_used_mb,
                    process_memory_mb,
                    available_memory_mb,
                    recorded_at
                FROM resource_monitor_logs
                ORDER BY recorded_at DESC
                LIMIT %s
                """,
                (limit,)
            )

            records = cursor.fetchall()

        return {
            "total_records": len(records),
            "history": records
        }

    except Exception:
        logger.exception("OS history failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch OS monitoring history"
        )

    finally:
        if connection:
            connection.close()
