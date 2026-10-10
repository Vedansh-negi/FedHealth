
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

from database.federated_db import get_federated_connection
from ml.model_config import FEATURE_COLUMNS, TARGET_COLUMN


TEST_DATA_PATH = "/Users/vedanshnegi/Downloads/common_test.csv"


def transform_features(df):
    """Apply the same transformations used during local training."""
    X = df[FEATURE_COLUMNS].astype(float).copy()

    X["bmi"] = X["bmi"] / 100.0
    X["genhlth"] = (X["genhlth"] - 1) / 4.0
    X["menthlth"] = X["menthlth"] / 30.0
    X["physhlth"] = X["physhlth"] / 30.0
    X["age"] = (X["age"] - 1) / 12.0
    X["education"] = (X["education"] - 1) / 5.0
    X["income"] = (X["income"] - 1) / 7.0

    return X


def evaluate_global_model():
    print("Loading common test dataset...")

    df = pd.read_csv(TEST_DATA_PATH)

    # CSV column names may use uppercase letters.
    df.columns = [
        col.strip().lower().replace(" ", "").replace("-", "")
        for col in df.columns
    ]

    missing = set(FEATURE_COLUMNS + [TARGET_COLUMN]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in test CSV: {sorted(missing)}")

    X = transform_features(df)
    y_true = df[TARGET_COLUMN].astype(int).to_numpy()

    conn = get_federated_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT global_model_id, model_version, weights, bias
                FROM global_models
                ORDER BY global_model_id DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

            if row is None:
                raise ValueError("No global model found in the database.")

            model_id, model_version, weights, bias = row

            weights = np.asarray(weights, dtype=float)
            bias = float(bias)

            if len(weights) != len(FEATURE_COLUMNS):
                raise ValueError(
                    f"Expected {len(FEATURE_COLUMNS)} weights, "
                    f"found {len(weights)}."
                )

            if not np.isfinite(weights).all() or not np.isfinite(bias):
                raise ValueError("Global model has invalid parameters.")

            # Logistic regression: sigmoid(Xw + b)
            logits = X.to_numpy() @ weights + bias

            # Numerically stable sigmoid.
            probabilities = np.empty_like(logits, dtype=float)
            positive = logits >= 0
            probabilities[positive] = (
                1 / (1 + np.exp(-logits[positive]))
            )
            exp_logits = np.exp(logits[~positive])
            probabilities[~positive] = (
                exp_logits / (1 + exp_logits)
            )

            predictions = (probabilities >= 0.5).astype(int)

            accuracy = accuracy_score(y_true, predictions)
            precision = precision_score(
                y_true, predictions, zero_division=0
            )
            recall = recall_score(
                y_true, predictions, zero_division=0
            )
            f1 = f1_score(
                y_true, predictions, zero_division=0
            )
            auc = roc_auc_score(y_true, probabilities)
            cm = confusion_matrix(y_true, predictions, labels=[0, 1])

            cur.execute(
                """
                UPDATE global_models
                SET accuracy = %s,
                    precision_score = %s,
                    recall_score = %s,
                    f1_score = %s
                WHERE global_model_id = %s
                """,
                (accuracy, precision, recall, f1, model_id),
            )

        conn.commit()

        print("\n" + "=" * 55)
        print("FEDHEALTH: GLOBAL MODEL EVALUATION")
        print("=" * 55)
        print(f"Model version : {model_version}")
        print(f"Test samples  : {len(y_true)}")
        print(f"Accuracy      : {accuracy:.4f}")
        print(f"Precision     : {precision:.4f}")
        print(f"Recall        : {recall:.4f}")
        print(f"F1 score      : {f1:.4f}")
        print(f"ROC-AUC       : {auc:.4f}")

        print("\nConfusion Matrix")
        print("Rows = actual, columns = predicted")
        print("                 Predicted 0  Predicted 1")
        print(f"Actual 0         {cm[0, 0]:10d}  {cm[0, 1]:11d}")
        print(f"Actual 1         {cm[1, 0]:10d}  {cm[1, 1]:11d}")

        print("\nClassification Report")
        print(classification_report(
            y_true,
            predictions,
            labels=[0, 1],
            target_names=["No diabetes", "Diabetes"],
            zero_division=0,
        ))

        print("Metrics saved to PostgreSQL.")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    evaluate_global_model()
