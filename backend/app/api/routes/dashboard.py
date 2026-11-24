import logging

from fastapi import APIRouter
from psycopg2.extras import RealDictCursor

from database.federated_db import get_federated_connection
from database.hospital_db import HOSPITAL_IDS, get_hospital_connection
from ml.model_config import MODEL_VERSION, get_config_fingerprint

logger = logging.getLogger("fedhealth.dashboard")

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


def hospital_counts():
    """Aggregate counts per hospital. No patient-level data is returned."""
    stats = []

    for hospital_id in HOSPITAL_IDS:
        connection = None
        try:
            connection = get_hospital_connection(hospital_id)

            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM patients")
                patients = cursor.fetchone()["total"]

                cursor.execute("SELECT COUNT(*) AS total FROM doctors")
                doctors = cursor.fetchone()["total"]

                cursor.execute("SELECT COUNT(*) AS total FROM appointments")
                appointments = cursor.fetchone()["total"]

                cursor.execute(
                    "SELECT COUNT(*) AS total FROM patient_health_data"
                )
                ml_dataset_records = cursor.fetchone()["total"]

            stats.append({
                "hospital_id": hospital_id,
                "patients": patients,
                "doctors": doctors,
                "appointments": appointments,
                "ml_dataset_records": ml_dataset_records
            })

        except Exception:
            logger.exception(
                "Dashboard stats failed for hospital %s", hospital_id
            )
            stats.append({
                "hospital_id": hospital_id,
                "error": "Statistics unavailable"
            })

        finally:
            if connection:
                connection.close()

    return stats

def federated_overview():
    """Completed round count and metrics of the latest evaluated model."""
    connection = None

    try:
        connection = get_federated_connection()

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM federated_rounds "
                "WHERE status = 'COMPLETED'"
            )
            rounds = cursor.fetchone()["total"]
            cursor.execute(
                """
                SELECT
                     gm.model_version,
                     fr.round_number,
                     gm.accuracy,
                     gm.precision_score,
                     gm.recall_score,
                     gm.f1_score,
                     gm.created_at
                FROM global_models gm
                LEFT JOIN federated_rounds fr
                     ON fr.round_id = gm.round_id
                WHERE gm.model_version LIKE %s
                     AND gm.config_fingerprint = %s
                ORDER BY gm.global_model_id DESC
                LIMIT 1
                """,
                (
                    f"{MODEL_VERSION}%",
                    get_config_fingerprint(),
                )
            )
            model = cursor.fetchone()

        latest = None

        if model:
            latest = {
                "model_version": model["model_version"],
                "round_number": model["round_number"],
                "accuracy": model["accuracy"],
                "precision": model["precision_score"],
                "recall": model["recall_score"],
                "f1_score": model["f1_score"],
                "evaluated": model["accuracy"] is not None,
                "created_at": model["created_at"]
            }

        return rounds, latest

    except Exception:
        logger.exception("Federated overview failed")
        return None, None

    finally:
        if connection:
            connection.close()


@router.get("")
@router.get("/", include_in_schema=False)
def dashboard():
    rounds, latest_model = federated_overview()

    return {
        "message": "Dashboard statistics",
        "hospitals": hospital_counts(),
        "federated_rounds": rounds,
        "latest_model": latest_model
    }
