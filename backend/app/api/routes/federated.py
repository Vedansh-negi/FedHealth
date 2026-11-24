
import logging
import threading

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.core.audit import log_audit
from app.core.security import ADMIN, DOCTOR, require_roles
from database.federated_db import get_federated_connection


logger = logging.getLogger("fedhealth.federated")

router = APIRouter(
    prefix="/api/federated",
    tags=["Federated Learning"]
)

# One training run at a time inside this server process.
_training_lock = threading.Lock()

# A round left in RUNNING for longer than this is treated as crashed.
STALE_AFTER_MINUTES = 30


def _safe_audit(hospital_id, user_id, action):
    try:
        log_audit(
            hospital_id,
            user_id,
            action,
            "federated_round"
        )
    except Exception:
        logger.exception("Failed to write audit event: %s", action)


def _run_training_job(user_id, hospital_id):
    """Run one protected federated training job followed by evaluation."""

    try:
        from ml.federated_learning import run_federated_round
        from ml.evaluate_global_model import evaluate_global_model

        # Stage 1: Federated training
        try:
            run_federated_round()
        except Exception:
            logger.exception("Federated training failed")
            _safe_audit(
                hospital_id,
                user_id,
                "FEDERATED_ROUND_FAILED"
            )
            return

        # Stage 2: Global model evaluation
        try:
            evaluate_global_model()
        except Exception:
            logger.exception(
                "Training completed, but global model evaluation failed"
            )
            _safe_audit(
                hospital_id,
                user_id,
                "FEDERATED_TRAINING_COMPLETED_EVALUATION_FAILED"
            )
            return

        # Both stages succeeded
        _safe_audit(
            hospital_id,
            user_id,
            "FEDERATED_ROUND_COMPLETED"
        )

    except Exception:
        logger.exception("Unexpected federated training job failure")
        _safe_audit(
            hospital_id,
            user_id,
            "FEDERATED_ROUND_FAILED"
        )

    finally:
        _training_lock.release()


def _running_round(cursor):
    cursor.execute(
        """
        SELECT round_id, round_number
        FROM federated_rounds
        WHERE status = 'RUNNING'
          AND start_time > NOW() - (%s * INTERVAL '1 minute')
        LIMIT 1
        """,
        (STALE_AFTER_MINUTES,)
    )
    return cursor.fetchone()


@router.get(
    "/summary",
    dependencies=[Depends(require_roles(ADMIN, DOCTOR))]
)
def federated_summary(limit: int = Query(10, ge=1, le=50)):
    connection = None

    try:
        connection = get_federated_connection()

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    fr.round_id,
                    fr.round_number,
                    fr.status,
                    fr.global_model_version,
                    fr.aggregation_method,
                    fr.start_time,
                    fr.end_time,
                    gm.accuracy,
                    gm.precision_score AS precision,
                    gm.recall_score AS recall,
                    gm.f1_score
                FROM federated_rounds fr
                LEFT JOIN global_models gm ON gm.round_id = fr.round_id
                ORDER BY fr.round_number DESC
                LIMIT %s
                """,
                (limit,)
            )

            rounds = cursor.fetchall()
            latest_round_id = rounds[0]["round_id"] if rounds else None
            hospital_updates = []

            if latest_round_id is not None:
                cursor.execute(
                    """
                    SELECT
                        hospital_id,
                        sample_count,
                        accuracy,
                        precision_score AS precision,
                        recall_score AS recall,
                        f1_score,
                        loss,
                        training_time_seconds
                    FROM model_updates
                    WHERE round_id = %s
                    ORDER BY hospital_id
                    """,
                    (latest_round_id,)
                )
                hospital_updates = cursor.fetchall()

            running = _running_round(cursor)

        return {
            "total_rounds": len(rounds),
            "training_in_progress": (
                bool(running) or _training_lock.locked()
            ),
            "rounds": rounds,
            "latest_hospital_updates": hospital_updates
        }

    except Exception:
        logger.exception("Federated summary failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to load federated learning data"
        )

    finally:
        if connection:
            connection.close()


@router.get(
    "/comparison",
    dependencies=[Depends(require_roles(ADMIN, DOCTOR))]
)
def federated_comparison():
    connection = None

    try:
        connection = get_federated_connection()

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT comparison_run
                FROM model_comparison
                ORDER BY comparison_id DESC
                LIMIT 1
                """
            )

            latest = cursor.fetchone()

            if not latest:
                return {
                    "comparison_run": None,
                    "results": []
                }

            comparison_run = latest["comparison_run"]

            cursor.execute(
                """
                SELECT
                    model_name,
                    accuracy,
                    precision_score AS precision,
                    recall_score AS recall,
                    f1_score,
                    roc_auc,
                    evaluation_set
                FROM model_comparison
                WHERE comparison_run = %s
                ORDER BY comparison_id
                """,
                (comparison_run,)
            )

            results = cursor.fetchall()

        return {
            "comparison_run": comparison_run,
            "results": results
        }

    except Exception:
        logger.exception("Federated comparison retrieval failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to load model comparison results"
        )

    finally:
        if connection:
            connection.close()


@router.post("/run", status_code=202)
def start_federated_round(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_roles(ADMIN))
):
    """Start one federated round in the background (admin only)."""

    # Acquire the lock before scheduling the background task.
    if not _training_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="A training round is already in progress"
        )

    lock_transferred = False
    connection = None

    try:
        connection = get_federated_connection()

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            running = _running_round(cursor)

        if running:
            raise HTTPException(
                status_code=409,
                detail="A training round is already in progress"
            )

        log_audit(
            current_user["hospital_id"],
            current_user["user_id"],
            "FEDERATED_ROUND_STARTED",
            "federated_round"
        )

        background_tasks.add_task(
            _run_training_job,
            current_user["user_id"],
            current_user["hospital_id"]
        )

        # The background job now owns responsibility for releasing the lock.
        lock_transferred = True

        return {
            "message": "Federated training round started"
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Could not start federated training")
        raise HTTPException(
            status_code=503,
            detail="Unable to start federated training"
        )

    finally:
        if connection:
            connection.close()

        if not lock_transferred:
            _training_lock.release()

