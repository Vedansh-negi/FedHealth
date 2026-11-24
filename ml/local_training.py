
import math
import time
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from database.hospital_db import get_hospital_connection
from ml.model_config import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    MODEL_VERSION,
    get_config_fingerprint,
)

LOCAL_EPOCHS = 5
BATCH_SIZE = 1024
LEARNING_RATE = 0.05
L2_STRENGTH = 0.001
RANDOM_SEED = 42


def transform_features(df):
    """Use exactly the same fixed transformations at every hospital."""
    X = df[FEATURE_COLUMNS].astype(float).copy()
    X["bmi"] = X["bmi"] / 100.0
    X["genhlth"] = (X["genhlth"] - 1) / 4.0
    X["menthlth"] = X["menthlth"] / 30.0
    X["physhlth"] = X["physhlth"] / 30.0
    X["age"] = (X["age"] - 1) / 12.0
    X["education"] = (X["education"] - 1) / 5.0
    X["income"] = (X["income"] - 1) / 7.0
    return X


def sigmoid(logits):
    """Numerically stable sigmoid."""
    logits = np.asarray(logits, dtype=float)
    probabilities = np.empty_like(logits)

    positive = logits >= 0
    probabilities[positive] = 1.0 / (
        1.0 + np.exp(-logits[positive])
    )

    exp_values = np.exp(logits[~positive])
    probabilities[~positive] = (
        exp_values / (1.0 + exp_values)
    )

    return probabilities


def prepare_local_training(
    hospital_id,
    round_number=1,
    initial_weights=None,
    initial_bias=0.0,
    local_epochs=LOCAL_EPOCHS,
):
    """Load and prepare one hospital's local task for cooperative scheduling."""

    if local_epochs <= 0:
        raise ValueError("local_epochs must be greater than zero.")

    print("\n" + "=" * 50)
    print(f"Preparing local training - Hospital {hospital_id}")
    print(f"Federated Round: {round_number}")
    print("=" * 50)

    conn = get_hospital_connection(hospital_id)

    try:
        query = f"""
            SELECT {", ".join(FEATURE_COLUMNS)}, {TARGET_COLUMN}
            FROM patient_health_data
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    print(f"Records loaded: {len(df)}")

    if df.empty:
        raise ValueError(
            f"Hospital {hospital_id} has no training records."
        )

    X = transform_features(df).to_numpy(dtype=np.float64)
    y = df[TARGET_COLUMN].astype(int).to_numpy(dtype=np.float64)

    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=RANDOM_SEED,
        stratify=y,
    )

    feature_count = X_train.shape[1]

    if initial_weights is None:
        weights = np.zeros(feature_count, dtype=np.float64)
    else:
        weights = np.asarray(
            initial_weights,
            dtype=np.float64
        ).copy()

        if weights.shape != (feature_count,):
            raise ValueError(
                f"Initial model has {weights.size} weights; "
                f"expected {feature_count}."
            )

    bias = float(initial_bias)

    if not np.isfinite(weights).all() or not np.isfinite(bias):
        raise ValueError(
            "Initial global parameters contain invalid values."
        )

    positive_count = max(
        float(np.sum(y_train == 1)), 1.0
    )
    negative_count = max(
        float(np.sum(y_train == 0)), 1.0
    )

    positive_weight = len(y_train) / (2.0 * positive_count)
    negative_weight = len(y_train) / (2.0 * negative_count)

    sample_weights = np.where(
        y_train == 1,
        positive_weight,
        negative_weight
    )

    batches_per_epoch = math.ceil(
        len(y_train) / BATCH_SIZE
    )

    return {
        "hospital_id": hospital_id,
        "round_number": round_number,
        "X_train": X_train,
        "y_train": y_train,
        "X_val": X_val,
        "y_val": y_val,
        "sample_weights": sample_weights,
        "weights": weights,
        "bias": bias,
        "local_epochs": local_epochs,
        "batches_per_epoch": batches_per_epoch,
        "total_batches": batches_per_epoch * local_epochs,
        "epoch": 0,
        "batch_order": None,
        "batch_start": 0,
        "rng": np.random.default_rng(
            RANDOM_SEED + hospital_id + round_number * 100
        ),
        "training_compute_seconds": 0.0,
        "started_at": datetime.now(),
        "completed_batches": 0,
    }


def train_one_local_batch(task):
    """Execute exactly one mini-batch; return False when task is complete."""

    if task["completed_batches"] >= task["total_batches"]:
        return False

    if (
        task["batch_order"] is None
        or task["batch_start"] >= len(task["batch_order"])
    ):
        task["epoch"] += 1
        task["batch_order"] = task["rng"].permutation(
            len(task["y_train"])
        )
        task["batch_start"] = 0

    start = task["batch_start"]
    end = min(start + BATCH_SIZE, len(task["y_train"]))

    indices = task["batch_order"][start:end]

    xb = task["X_train"][indices]
    yb = task["y_train"][indices]
    sw = task["sample_weights"][indices]

    compute_started = time.perf_counter()

    probabilities = sigmoid(
        xb @ task["weights"] + task["bias"]
    )

    errors = (probabilities - yb) * sw
    denominator = max(float(np.sum(sw)), 1.0)

    grad_weights = (xb.T @ errors) / denominator
    grad_weights += L2_STRENGTH * task["weights"]

    grad_bias = float(np.sum(errors) / denominator)

    task["weights"] -= LEARNING_RATE * grad_weights
    task["bias"] -= LEARNING_RATE * grad_bias

    task["training_compute_seconds"] += (
        time.perf_counter() - compute_started
    )

    task["batch_start"] = end
    task["completed_batches"] += 1

    return True


def finalize_local_training(task):
    """Evaluate and persist a completed local task."""

    if task["completed_batches"] != task["total_batches"]:
        raise RuntimeError(
            f"Hospital {task['hospital_id']} training is not complete."
        )

    val_prob = np.clip(
        sigmoid(
            task["X_val"] @ task["weights"] + task["bias"]
        ),
        1e-7,
        1 - 1e-7,
    )

    val_pred = (val_prob >= 0.5).astype(int)

    accuracy = accuracy_score(task["y_val"], val_pred)

    precision = precision_score(
        task["y_val"],
        val_pred,
        zero_division=0
    )

    recall = recall_score(
        task["y_val"],
        val_pred,
        zero_division=0
    )

    f1 = f1_score(
        task["y_val"],
        val_pred,
        zero_division=0
    )

    loss = log_loss(
        task["y_val"],
        val_prob,
        labels=[0, 1]
    )

    now = datetime.now()

    conn = get_hospital_connection(task["hospital_id"])

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO training_runs (
                    round_number,
                    model_version,
                    sample_count,
                    accuracy,
                    precision_score,
                    recall_score,
                    f1_score,
                    loss,
                    training_time_seconds,
                    started_at,
                    completed_at,
                    status
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    task["round_number"],
                    f"{MODEL_VERSION}-fedavg",
                    len(task["y_train"]),
                    accuracy,
                    precision,
                    recall,
                    f1,
                    loss,
                    task["training_compute_seconds"],
                    task["started_at"],
                    now,
                    "COMPLETED",
                ),
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    print("\nLocal Training Results")
    print("-" * 30)
    print(f"Hospital          : {task['hospital_id']}")
    print(f"Training samples  : {len(task['y_train'])}")
    print(f"Validation samples: {len(task['y_val'])}")
    print(f"Accuracy          : {accuracy:.4f}")
    print(f"Precision         : {precision:.4f}")
    print(f"Recall            : {recall:.4f}")
    print(f"F1 Score          : {f1:.4f}")
    print(f"Log Loss          : {loss:.4f}")
    print(
        f"Training compute  : "
        f"{task['training_compute_seconds']:.3f} seconds"
    )
    print(f"Local epochs      : {task['local_epochs']}")
    print(f"Updated local bias: {task['bias']:.6f}")

    return {
        "hospital_id": task["hospital_id"],
        "round_number": task["round_number"],
        "sample_count": len(task["y_train"]),
        "weights": task["weights"].tolist(),
        "bias": float(task["bias"]),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "loss": float(loss),
        "training_time_seconds": float(
            task["training_compute_seconds"]
        ),
        "model_version": MODEL_VERSION,
        "config_fingerprint": get_config_fingerprint(),
    }


def train_local_model(
    hospital_id,
    round_number=1,
    initial_weights=None,
    initial_bias=0.0,
    local_epochs=LOCAL_EPOCHS,
):
    """Backward-compatible standalone training using the same mini-batch steps."""

    task = prepare_local_training(
        hospital_id=hospital_id,
        round_number=round_number,
        initial_weights=initial_weights,
        initial_bias=initial_bias,
        local_epochs=local_epochs,
    )

    while train_one_local_batch(task):
        pass

    return finalize_local_training(task)


if __name__ == "__main__":
    train_local_model(hospital_id=1, round_number=1)
