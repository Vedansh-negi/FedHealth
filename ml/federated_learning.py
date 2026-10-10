import json
import math
from datetime import datetime

import numpy as np
from psycopg2.extras import Json

from database.federated_db import get_federated_connection
from ml.local_training import train_local_model
from ml.model_config import (
    FEATURE_COLUMNS,
    MODEL_VERSION,
    get_config_fingerprint,
)

HOSPITAL_IDS = (1, 2, 3)


def create_federated_round(conn):
    """Create the next round number."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(MAX(round_number), 0) + 1 FROM federated_rounds"
        )
        round_number = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO federated_rounds (
                round_number, global_model_version, start_time,
                status, aggregation_method
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING round_id
            """,
            (
                round_number,
                MODEL_VERSION,
                datetime.now(),
                "RUNNING",
                "Iterative FedAvg (mini-batch SGD)",
            ),
        )
        round_id = cur.fetchone()[0]
    conn.commit()
    return round_id, round_number


def load_initial_global_model(conn):
    """
    Continue from the latest compatible model if one exists.
    If no compatible model exists, all hospitals start from zeros.
    """
    expected_fingerprint = get_config_fingerprint()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT weights, bias, config_fingerprint, model_version
            FROM global_models
            WHERE config_fingerprint = %s
            ORDER BY global_model_id DESC
            LIMIT 1
            """,
            (expected_fingerprint,),
        )
        row = cur.fetchone()

    if row is None:
        print("No compatible global model found; starting from zero parameters.")
        return np.zeros(len(FEATURE_COLUMNS), dtype=float), 0.0, None

    weights, bias, fingerprint, model_version = row
    weights = np.asarray(weights, dtype=float)
    bias = float(bias)

    if fingerprint != expected_fingerprint:
        raise ValueError("Global model configuration fingerprint mismatch.")
    if weights.shape != (len(FEATURE_COLUMNS),):
        raise ValueError("Stored global model has the wrong number of weights.")
    if not np.isfinite(weights).all() or not math.isfinite(bias):
        raise ValueError("Stored global model contains invalid parameters.")

    print(f"Starting from previous global model: {model_version}")
    return weights, bias, model_version


def validate_update(result, expected_fingerprint):
    if result["model_version"] != MODEL_VERSION:
        raise ValueError(
            f"Hospital {result['hospital_id']}: model version mismatch"
        )
    if result["config_fingerprint"] != expected_fingerprint:
        raise ValueError(
            f"Hospital {result['hospital_id']}: configuration mismatch"
        )

    weights = np.asarray(result["weights"], dtype=float)
    bias = float(result["bias"])
    if weights.shape != (len(FEATURE_COLUMNS),):
        raise ValueError(
            f"Hospital {result['hospital_id']}: invalid number of weights"
        )
    if not np.isfinite(weights).all() or not math.isfinite(bias):
        raise ValueError(
            f"Hospital {result['hospital_id']}: invalid model parameters"
        )
    if int(result["sample_count"]) <= 0:
        raise ValueError(
            f"Hospital {result['hospital_id']}: sample count must be positive"
        )


def aggregate_models(results):
    """Sample-count-weighted parameter aggregation (FedAvg)."""
    if not results:
        raise ValueError("No hospital updates were supplied.")

    total_samples = sum(int(result["sample_count"]) for result in results)
    if total_samples <= 0:
        raise ValueError("Total sample count must be positive.")

    global_weights = np.zeros(len(FEATURE_COLUMNS), dtype=float)
    global_bias = 0.0

    for result in results:
        contribution = int(result["sample_count"]) / total_samples
        global_weights += contribution * np.asarray(result["weights"], dtype=float)
        global_bias += contribution * float(result["bias"])

    return global_weights.tolist(), float(global_bias)


def run_federated_round():
    conn = get_federated_connection()
    round_id = None
    try:
        round_id, round_number = create_federated_round(conn)
        print("\n" + "=" * 58)
        print(f"FEDHEALTH: ITERATIVE FEDAVG ROUND {round_number}")
        print("=" * 58)

        expected_fingerprint = get_config_fingerprint()
        initial_weights, initial_bias, previous_version = load_initial_global_model(conn)
        print(f"Starting bias: {initial_bias:.6f}")
        if previous_version:
            print(f"Previous global version: {previous_version}")

        results = []
        for hospital_id in HOSPITAL_IDS:
            print(f"\nTraining Hospital {hospital_id} from the same global model...")
            result = train_local_model(
                hospital_id=hospital_id,
                round_number=round_number,
                initial_weights=initial_weights,
                initial_bias=initial_bias,
            )
            validate_update(result, expected_fingerprint)
            results.append(result)

        global_weights, global_bias = aggregate_models(results)
        new_version = f"{MODEL_VERSION}-fedavg-round-{round_number}"

        with conn.cursor() as cur:
            for result in results:
                payload = {
                    "weights": result["weights"],
                    "bias": result["bias"],
                    "model_version": result["model_version"],
                }
                payload_size = len(
                    json.dumps(payload, separators=(",", ":")).encode("utf-8")
                )

                cur.execute(
                    """
                    INSERT INTO model_updates (
                        hospital_id, round_id, sample_count, weights, bias,
                        accuracy, precision_score, recall_score, f1_score,
                        loss, training_time_seconds, model_version,
                        config_fingerprint
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        result["hospital_id"],
                        round_id,
                        result["sample_count"],
                        Json(result["weights"]),
                        Json(result["bias"]),
                        result["accuracy"],
                        result["precision"],
                        result["recall"],
                        result["f1_score"],
                        result["loss"],
                        result["training_time_seconds"],
                        result["model_version"],
                        result["config_fingerprint"],
                    ),
                )

                # Payload size is estimated from serialized parameters;
                # communication time is not measured in this local prototype.
                cur.execute(
                    """
                    INSERT INTO communication_logs (
                        round_id, hospital_id, data_size_bytes,
                        communication_time_seconds, status
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        round_id,
                        result["hospital_id"],
                        payload_size,
                        0.0,
                        "SIMULATED",
                    ),
                )

            cur.execute(
                """
                INSERT INTO global_models (
                    round_id, model_version, weights, bias, config_fingerprint
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    round_id,
                    new_version,
                    Json(global_weights),
                    Json(global_bias),
                    expected_fingerprint,
                ),
            )
            cur.execute(
                """
                UPDATE federated_rounds
                SET status = %s, end_time = %s, global_model_version = %s,
                    aggregation_method = %s
                WHERE round_id = %s
                """,
                (
                    "COMPLETED",
                    datetime.now(),
                    new_version,
                    "Iterative FedAvg (mini-batch SGD)",
                    round_id,
                ),
            )

        conn.commit()

        print("\n" + "=" * 58)
        print("ITERATIVE FEDAVG ROUND COMPLETED")
        print("=" * 58)
        for result in results:
            print(
                f"Hospital {result['hospital_id']} | "
                f"Training samples: {result['sample_count']} | "
                f"F1: {result['f1_score']:.4f}"
            )
        print(f"Global weights: {len(global_weights)}")
        print(f"Starting bias: {initial_bias:.6f}")
        print(f"Aggregated bias: {global_bias:.6f}")
        print(f"Model version: {new_version}")
        print("Patient records transferred to aggregator: NO")
        print("Note: parameter payload sizes are estimates; network traffic is not measured.")

    except Exception:
        conn.rollback()
        if round_id is not None:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE federated_rounds
                        SET status = %s, end_time = %s
                        WHERE round_id = %s
                        """,
                        ("FAILED", datetime.now(), round_id),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_federated_round()
