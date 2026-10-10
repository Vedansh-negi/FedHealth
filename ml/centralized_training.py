
import time
import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

from psycopg2.extras import Json

from database.hospital_db import get_hospital_connection
from database.federated_db import get_federated_connection
from ml.model_config import FEATURE_COLUMNS, TARGET_COLUMN, MODEL_VERSION


TEST_DATA_PATH = "/Users/vedanshnegi/Downloads/common_test.csv"


def transform_features(df):
    X = df[FEATURE_COLUMNS].astype(float).copy()

    X["bmi"] = X["bmi"] / 100.0
    X["genhlth"] = (X["genhlth"] - 1) / 4.0
    X["menthlth"] = X["menthlth"] / 30.0
    X["physhlth"] = X["physhlth"] / 30.0
    X["age"] = (X["age"] - 1) / 12.0
    X["education"] = (X["education"] - 1) / 5.0
    X["income"] = (X["income"] - 1) / 7.0

    return X


def get_metrics(y_true, probabilities):
    predictions = (probabilities >= 0.5).astype(int)

    return {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(
            precision_score(y_true, predictions, zero_division=0)
        ),
        "recall": float(
            recall_score(y_true, predictions, zero_division=0)
        ),
        "f1_score": float(
            f1_score(y_true, predictions, zero_division=0)
        ),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
    }


def predict_probabilities(X, weights, bias):
    logits = np.asarray(X) @ np.asarray(weights, dtype=float) + float(bias)

    # Numerically stable sigmoid
    probabilities = np.empty_like(logits, dtype=float)
    positive = logits >= 0

    probabilities[positive] = 1 / (1 + np.exp(-logits[positive]))

    exp_logits = np.exp(logits[~positive])
    probabilities[~positive] = exp_logits / (1 + exp_logits)

    return probabilities


def evaluate_saved_parameters(X_test, y_test, weights, bias):
    probabilities = predict_probabilities(X_test, weights, bias)
    return get_metrics(y_test, probabilities)


def run_comparison():
    print("=" * 60)
    print("FEDHEALTH: LOCAL VS FEDERATED VS CENTRALIZED")
    print("=" * 60)

    # Load the common held-out test dataset.
    test_df = pd.read_csv(TEST_DATA_PATH)
    test_df.columns = [
        c.strip().lower().replace(" ", "").replace("-", "")
        for c in test_df.columns
    ]

    required = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    missing = required - set(test_df.columns)

    if missing:
        raise ValueError(f"Missing test columns: {sorted(missing)}")

    X_test = transform_features(test_df)
    y_test = test_df[TARGET_COLUMN].astype(int).to_numpy()

    # Load the three hospitals' training datasets.
    X_train_parts = []
    y_train_parts = []

    for hospital_id in range(1, 4):
        conn = get_hospital_connection(hospital_id)
        try:
            df = pd.read_sql_query(
                """
                SELECT *
                FROM patient_health_data
                ORDER BY patient_id
                """,
                conn,
            )
        finally:
            conn.close()

        X = transform_features(df)
        y = df[TARGET_COLUMN].astype(int)

        # Match the 80/20 local split and random seed used by
        # the existing local-training implementation.
        X_train, _, y_train, _ = train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y,
        )

        X_train_parts.append(X_train)
        y_train_parts.append(y_train)

    X_central = pd.concat(X_train_parts, ignore_index=True)
    y_central = pd.concat(y_train_parts, ignore_index=True)

    # Train the centralized baseline.
    print(f"\nCentralized training samples: {len(y_central)}")
    start = time.perf_counter()

    central_model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        solver="lbfgs",
        random_state=42,
    )
    central_model.fit(X_central, y_central)

    central_training_time = time.perf_counter() - start

    central_probabilities = central_model.predict_proba(X_test)[:, 1]
    central_metrics = get_metrics(y_test, central_probabilities)

    # Load the latest successfully completed federated round.
    conn = get_federated_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT round_id, global_model_id, model_version,
                       weights, bias
                FROM global_models
                WHERE round_id = (
                    SELECT round_id
                    FROM federated_rounds
                    WHERE status = 'COMPLETED'
                    ORDER BY round_number DESC
                    LIMIT 1
                )
                ORDER BY global_model_id DESC
                LIMIT 1
                """
            )
            global_row = cur.fetchone()

            if global_row is None:
                raise ValueError("No completed global model found.")

            round_id, global_model_id, global_version, global_weights, global_bias = global_row

            cur.execute(
                """
                SELECT DISTINCT ON (hospital_id)
                       hospital_id, weights, bias
                FROM model_updates
                WHERE round_id = %s
                ORDER BY hospital_id, update_id DESC
                """,
                (round_id,),
            )
            local_rows = cur.fetchall()

            if len(local_rows) != 3:
                raise ValueError(
                    f"Expected 3 hospital updates; found {len(local_rows)}."
                )

            # Create tables to persist the baseline and comparison.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS centralized_models (
                    centralized_model_id SERIAL PRIMARY KEY,
                    model_version VARCHAR(100) NOT NULL,
                    training_samples INTEGER NOT NULL,
                    accuracy DECIMAL(6,4),
                    precision_score DECIMAL(6,4),
                    recall_score DECIMAL(6,4),
                    f1_score DECIMAL(6,4),
                    roc_auc DECIMAL(6,4),
                    training_time_seconds DECIMAL(10,3),
                    weights JSONB NOT NULL,
                    bias DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS model_comparison (
                    comparison_id SERIAL PRIMARY KEY,
                    comparison_run VARCHAR(100) NOT NULL,
                    model_name VARCHAR(100) NOT NULL,
                    accuracy DECIMAL(6,4),
                    precision_score DECIMAL(6,4),
                    recall_score DECIMAL(6,4),
                    f1_score DECIMAL(6,4),
                    roc_auc DECIMAL(6,4),
                    evaluation_set VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Save centralized model and metrics.
            cur.execute(
                """
                INSERT INTO centralized_models (
                    model_version, training_samples, accuracy,
                    precision_score, recall_score, f1_score,
                    roc_auc, training_time_seconds, weights, bias
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING centralized_model_id
                """,
                (
                    "central-logreg-v1",
                    len(y_central),
                    central_metrics["accuracy"],
                    central_metrics["precision"],
                    central_metrics["recall"],
                    central_metrics["f1_score"],
                    central_metrics["roc_auc"],
                    central_training_time,
                    Json(central_model.coef_[0].tolist()),
                    float(central_model.intercept_[0]),
                ),
            )
            centralized_id = cur.fetchone()[0]

            comparison_run = f"comparison-{centralized_id}"

            comparison_results = []

            # Evaluate each hospital's local model on the common test set.
            for hospital_id, weights, bias in local_rows:
                metrics = evaluate_saved_parameters(
                    X_test, y_test, weights, bias
                )
                comparison_results.append(
                    (f"Hospital {hospital_id} local", metrics)
                )

            # Evaluate the global model.
            global_metrics = evaluate_saved_parameters(
                X_test, y_test, global_weights, global_bias
            )
            comparison_results.append(("Federated global", global_metrics))
            comparison_results.append(("Centralized", central_metrics))

            for model_name, metrics in comparison_results:
                cur.execute(
                    """
                    INSERT INTO model_comparison (
                        comparison_run, model_name, accuracy,
                        precision_score, recall_score, f1_score,
                        roc_auc, evaluation_set
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        comparison_run,
                        model_name,
                        metrics["accuracy"],
                        metrics["precision"],
                        metrics["recall"],
                        metrics["f1_score"],
                        metrics["roc_auc"],
                        "common_test.csv (held-out)",
                    ),
                )

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Print results.
    results = [
        {"Model": name, **metrics}
        for name, metrics in comparison_results
    ]

    results_df = pd.DataFrame(results).set_index("Model")

    print("\nHeld-out test results")
    print(results_df.round(4).to_string())

    print(f"\nCentralized training time: {central_training_time:.3f} seconds")
    print(f"Centralized model ID: {centralized_id}")
    print(f"Comparison run: {comparison_run}")
    print("Comparison results saved to PostgreSQL.")


if __name__ == "__main__":
    run_comparison()
