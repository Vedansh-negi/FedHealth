import logging

from fastapi import APIRouter

from database.hospital_db import HOSPITAL_IDS, get_hospital_connection


logger = logging.getLogger("fedhealth.hospitals")

router = APIRouter(
    prefix="/api/hospitals",
    tags=["Hospitals"]
)


def _is_reachable(hospital_id):
    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return True

    except Exception:
        logger.warning("Hospital %s database unreachable", hospital_id)
        return False

    finally:
        if connection:
            connection.close()


@router.get("")
@router.get("/", include_in_schema=False)
def get_hospitals():
    hospitals = [
        {
            "hospital_id": hospital_id,
            "hospital_name": f"Hospital {hospital_id}",
            "database_name": f"hospital_{hospital_id}_db",
            "status": (
                "connected" if _is_reachable(hospital_id)
                else "unreachable"
            )
        }
        for hospital_id in HOSPITAL_IDS
    ]

    return {
        "total_hospitals": len(hospitals),
        "hospitals": hospitals
    }
