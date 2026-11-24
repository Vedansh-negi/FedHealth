import numpy as np
import pandas as pd

from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split

from database.federated_db import get_federated_connection
from database.hospital_db import get_hospital_connection
from ml.model_config import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    MODEL_VERSION,
    get_config_fingerprint,
)
from ml.local_training import transform_features, sigmoid


def evaluate_global_model():

    print("\nLoading latest global model...")

    conn = get_federated_connection()

    try:
        with conn.cursor() as cur:
           cur.execute("""
             SELECT global_model_id, model_version, weights, bias
             FROM global_models
             WHERE model_version LIKE %s
             AND config_fingerprint = %s
             ORDER BY global_model_id DESC
             LIMIT 1
             """, (
              f"{MODEL_VERSION}%",
             get_config_fingerprint(),
             ))
           model = cur.fetchone()

        if model is None:
            raise ValueError("No global model found.")

        model_id, model_version, weights, bias = model

        weights = np.asarray(weights, dtype=float)
        bias = float(bias)

        if weights.shape != (len(FEATURE_COLUMNS),):
            raise ValueError("Global model has an incorrect number of weights.")

        if not np.isfinite(weights).all() or not np.isfinite(bias):
            raise ValueError("Global model contains invalid parameters.")

        # Only aggregate confusion-matrix counts centrally.
        global_cm = np.zeros((2, 2), dtype=np.int64)

        # Evaluate each hospital's local validation data.
        for hospital_id in (1, 2, 3):

            print(f"\nEvaluating Hospital {hospital_id}...")

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
                raise ValueError(
                    f"Hospital {hospital_id} has no records."
                )

            _, validation_df = train_test_split(
                df,
                test_size=0.20,
                random_state=42,
                stratify=df[TARGET_COLUMN].astype(int),
            )

            X = transform_features(validation_df).to_numpy(dtype=float)

            y = validation_df[TARGET_COLUMN].astype(int).to_numpy()

            probabilities = sigmoid(X @ weights + bias)

            predictions = (probabilities >= 0.5).astype(int)

            # Calculate local confusion matrix.
            local_cm = confusion_matrix(
                y,
                predictions,
                labels=[0, 1],
            )

            # Only aggregate counts, not patient-level predictions.
            global_cm += local_cm

            print(
                f"Hospital {hospital_id}: "
                f"{len(validation_df):,} validation records evaluated."
            )

            print("Local confusion matrix:")
            print(local_cm)

            del df, validation_df, X, y, probabilities, predictions

        # Extract aggregated counts.
        tn, fp, fn, tp = global_cm.ravel()

        total = tn + fp + fn + tp

        if total == 0:
            raise ValueError("No validation records were evaluated.")

        accuracy = (tp + tn) / total

        precision = tp / (tp + fp) if (tp + fp) else 0.0

        recall = tp / (tp + fn) if (tp + fn) else 0.0

        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        accuracy = float(accuracy)
        precision = float(precision)
        recall = float(recall)
        f1 = float(f1)
        # Save aggregate metrics for the current global model.
        with conn.cursor() as cur:

            cur.execute("""
                UPDATE global_models
                SET accuracy = %s,
                    precision_score = %s,
                    recall_score = %s,
                    f1_score = %s
                WHERE global_model_id = %s
            """, (
                accuracy,
                precision,
                recall,
                f1,
                model_id,
            ))

        conn.commit()

        print("\n" + "=" * 55)
        print("FEDHEALTH PRIVACY-CONSCIOUS GLOBAL EVALUATION")
        print("=" * 55)

        print(f"Model version       : {model_version}")
        print(f"Evaluation records  : {total:,}")
        print(f"Accuracy            : {accuracy:.4f}")
        print(f"Precision           : {precision:.4f}")
        print(f"Recall              : {recall:.4f}")
        print(f"F1 Score            : {f1:.4f}")

        print("\nAggregated Confusion Matrix:")
        print(global_cm)

        print("\nAggregated counts:")
        print(f"True Negatives  : {tn:,}")
        print(f"False Positives : {fp:,}")
        print(f"False Negatives : {fn:,}")
        print(f"True Positives  : {tp:,}")

        print(
            "\nMetrics saved. These are validation-based results, "
            "not independent test-set results."
        )

        print(
            "\nROC-AUC is omitted because exact global ROC-AUC "
            "cannot be calculated from confusion-matrix counts alone."
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    evaluate_global_model()
