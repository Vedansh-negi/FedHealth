
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
from database.hospital_db import get_hospital_connection
from ml.model_config import FEATURE_COLUMNS, TARGET_COLUMN
from ml.local_training import transform_features, sigmoid


def evaluate_global_model():
    print("\nLoading latest global model...")

    conn = get_federated_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT global_model_id, model_version, weights, bias
                FROM global_models
                ORDER BY global_model_id DESC
                LIMIT 1
            """)
            model = cur.fetchone()

        if model is None:
            raise ValueError("No global model found. Run federated training first.")

        model_id, model_version, weights, bias = model
        weights = np.asarray(weights, dtype=float)
        bias = float(bias)

        if len(weights) != len(FEATURE_COLUMNS):
            raise ValueError("Global model has an incorrect number of weights.")

        if not np.isfinite(weights).all() or not np.isfinite(bias):
            raise ValueError("Global model contains invalid parameters.")

        all_y = []
        all_probabilities = []

        # Evaluate on each hospital's local 20% validation split.
        for hospital_id in (1, 2, 3):
            hospital_conn = get_hospital_connection(hospital_id)

            try:
                query = f"""
                    SELECT {", ".join(FEATURE_COLUMNS)}, {TARGET_COLUMN}
                    FROM patient_health_data
                """
                df = pd.read_sql_query(query, hospital_conn)
            finally:
                hospital_conn.close()

            if df.empty:
                raise ValueError(f"Hospital {hospital_id} has no records.")

            # Match the deterministic 80/20 split used by local training.
            from sklearn.model_selection import train_test_split

            _, validation_df = train_test_split(
                df,
                test_size=0.20,
                random_state=42,
                stratify=df[TARGET_COLUMN].astype(int),
            )

            X = transform_features(validation_df).to_numpy(dtype=float)
            y = validation_df[TARGET_COLUMN].astype(int).to_numpy()

            probabilities = np.clip(
                sigmoid(X @ weights + bias), 1e-7, 1 - 1e-7
            )

            all_y.extend(y.tolist())
            all_probabilities.extend(probabilities.tolist())

            print(
                f"Hospital {hospital_id}: "
                f"{len(validation_df):,} validation records evaluated"
            )

        y_true = np.asarray(all_y, dtype=int)
        probabilities = np.asarray(all_probabilities, dtype=float)
        predictions = (probabilities >= 0.5).astype(int)

        accuracy = accuracy_score(y_true, predictions)
        precision = precision_score(y_true, predictions, zero_division=0)
        recall = recall_score(y_true, predictions, zero_division=0)
        f1 = f1_score(y_true, predictions, zero_division=0)
        auc = roc_auc_score(y_true, probabilities)
        cm = confusion_matrix(y_true, predictions, labels=[0, 1])

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE global_models
                SET accuracy = %s,
                    precision_score = %s,
                    recall_score = %s,
                    f1_score = %s
                WHERE global_model_id = %s
            """, (accuracy, precision, recall, f1, model_id))

        conn.commit()

        print("\n" + "=" * 50)
        print("FEDHEALTH GLOBAL MODEL EVALUATION")
        print("=" * 50)
        print(f"Model version : {model_version}")
        print(f"Evaluation records: {len(y_true):,}")
        print(f"Accuracy      : {accuracy:.4f}")
        print(f"Precision     : {precision:.4f}")
        print(f"Recall        : {recall:.4f}")
        print(f"F1 Score      : {f1:.4f}")
        print(f"ROC-AUC       : {auc:.4f}")
        print("\nConfusion Matrix:")
        print(cm)
        print("\nClassification Report:")
        print(classification_report(
            y_true,
            predictions,
            labels=[0, 1],
            target_names=["No diabetes", "Diabetes"],
            zero_division=0,
        ))

        print(
            "\nMetrics saved. These are validation-based results, "
            "not independent test-set results."
        )

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    evaluate_global_model()
