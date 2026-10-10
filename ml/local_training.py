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

# Small-batch gradient descent makes it possible to start every hospital
# from the same global coefficients and perform genuine local FedAvg updates.
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
    probabilities[positive] = 1.0 / (1.0 + np.exp(-logits[positive]))
    exp_values = np.exp(logits[~positive])
    probabilities[~positive] = exp_values / (1.0 + exp_values)
    return probabilities


def train_local_model(
    hospital_id,
    round_number=1,
    initial_weights=None,
    initial_bias=0.0,
    local_epochs=LOCAL_EPOCHS,
):
    """
    Train one hospital's model starting from the supplied global parameters.
    Only the resulting weights and bias are returned to the aggregator.
    """
    print("\n" + "=" * 50)
    print(f"Starting local training - Hospital {hospital_id}")
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
        raise ValueError(f"Hospital {hospital_id} has no training records.")

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
        weights = np.asarray(initial_weights, dtype=np.float64).copy()
        if weights.shape != (feature_count,):
            raise ValueError(
                f"Initial model has {weights.size} weights; "
                f"expected {feature_count}."
            )

    bias = float(initial_bias)
    if not np.isfinite(weights).all() or not np.isfinite(bias):
        raise ValueError("Initial global parameters contain invalid values.")

    # Balanced class weights are calculated locally from this hospital's
    # training subset. They are used only during local optimization.
    positive_count = max(float(np.sum(y_train == 1)), 1.0)
    negative_count = max(float(np.sum(y_train == 0)), 1.0)
    positive_weight = len(y_train) / (2.0 * positive_count)
    negative_weight = len(y_train) / (2.0 * negative_count)
    sample_weights = np.where(y_train == 1, positive_weight, negative_weight)

    rng = np.random.default_rng(RANDOM_SEED + hospital_id + round_number * 100)
    start_time = time.perf_counter()

    for epoch in range(local_epochs):
        order = rng.permutation(len(y_train))
        X_shuffled = X_train[order]
        y_shuffled = y_train[order]
        sw_shuffled = sample_weights[order]

        for start in range(0, len(y_train), BATCH_SIZE):
            end = min(start + BATCH_SIZE, len(y_train))
            xb = X_shuffled[start:end]
            yb = y_shuffled[start:end]
            sw = sw_shuffled[start:end]

            probabilities = sigmoid(xb @ weights + bias)
            errors = (probabilities - yb) * sw
            denominator = max(float(np.sum(sw)), 1.0)

            grad_weights = (xb.T @ errors) / denominator
            grad_weights += L2_STRENGTH * weights
            grad_bias = float(np.sum(errors) / denominator)

            weights -= LEARNING_RATE * grad_weights
            bias -= LEARNING_RATE * grad_bias

    training_time = time.perf_counter() - start_time

    val_prob = np.clip(sigmoid(X_val @ weights + bias), 1e-7, 1 - 1e-7)
    val_pred = (val_prob >= 0.5).astype(int)

    accuracy = accuracy_score(y_val, val_pred)
    precision = precision_score(y_val, val_pred, zero_division=0)
    recall = recall_score(y_val, val_pred, zero_division=0)
    f1 = f1_score(y_val, val_pred, zero_division=0)
    loss = log_loss(y_val, val_prob, labels=[0, 1])

    now = datetime.now()
    conn = get_hospital_connection(hospital_id)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO training_runs (
                    round_number, model_version, sample_count, accuracy,
                    precision_score, recall_score, f1_score, loss,
                    training_time_seconds, started_at, completed_at, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    round_number,
                    f"{MODEL_VERSION}-fedavg",
                    len(X_train),
                    accuracy,
                    precision,
                    recall,
                    f1,
                    loss,
                    training_time,
                    now,
                    datetime.now(),
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
    print(f"Training samples : {len(X_train)}")
    print(f"Validation samples: {len(X_val)}")
    print(f"Accuracy         : {accuracy:.4f}")
    print(f"Precision        : {precision:.4f}")
    print(f"Recall           : {recall:.4f}")
    print(f"F1 Score         : {f1:.4f}")
    print(f"Log Loss         : {loss:.4f}")
    print(f"Training time    : {training_time:.3f} seconds")
    print(f"Local epochs     : {local_epochs}")
    print(f"Starting global bias: {initial_bias:.6f}")
    print(f"Updated local bias : {bias:.6f}")

    return {
        "hospital_id": hospital_id,
        "round_number": round_number,
        "sample_count": len(X_train),
        "weights": weights.tolist(),
        "bias": float(bias),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "loss": float(loss),
        "training_time_seconds": float(training_time),
        "model_version": MODEL_VERSION,
        "config_fingerprint": get_config_fingerprint(),
    }


if __name__ == "__main__":
    train_local_model(hospital_id=1, round_number=1)
