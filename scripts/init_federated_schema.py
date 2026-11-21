import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import psycopg2

from config.database import connection_kwargs


def main():
    conn = psycopg2.connect(**connection_kwargs("federated_db"))

    try:
        with conn.cursor() as cur:
            # 1. Federated learning rounds
            cur.execute("""
                CREATE TABLE IF NOT EXISTS federated_rounds (
                    round_id SERIAL PRIMARY KEY,
                    round_number INTEGER NOT NULL UNIQUE,
                    global_model_version VARCHAR(100),
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    status VARCHAR(30) NOT NULL,
                    aggregation_method VARCHAR(150)
                )
            """)

            # 2. Global model parameters and evaluation metrics
            cur.execute("""
                CREATE TABLE IF NOT EXISTS global_models (
                    global_model_id SERIAL PRIMARY KEY,
                    round_id INTEGER REFERENCES federated_rounds(round_id),
                    model_version VARCHAR(100) NOT NULL,
                    weights JSONB NOT NULL,
                    bias DOUBLE PRECISION NOT NULL,
                    config_fingerprint VARCHAR(128),
                    accuracy DOUBLE PRECISION,
                    precision_score DOUBLE PRECISION,
                    recall_score DOUBLE PRECISION,
                    f1_score DOUBLE PRECISION,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Individual hospital model updates
            cur.execute("""
                CREATE TABLE IF NOT EXISTS model_updates (
                    update_id SERIAL PRIMARY KEY,
                    hospital_id INTEGER NOT NULL,
                    round_id INTEGER NOT NULL
                        REFERENCES federated_rounds(round_id),
                    sample_count INTEGER NOT NULL,
                    weights JSONB NOT NULL,
                    bias DOUBLE PRECISION NOT NULL,
                    accuracy DOUBLE PRECISION,
                    precision_score DOUBLE PRECISION,
                    recall_score DOUBLE PRECISION,
                    f1_score DOUBLE PRECISION,
                    loss DOUBLE PRECISION,
                    training_time_seconds DOUBLE PRECISION,
                    model_version VARCHAR(100) NOT NULL,
                    config_fingerprint VARCHAR(128),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. Simulated communication records
            cur.execute("""
                CREATE TABLE IF NOT EXISTS communication_logs (
                    communication_log_id SERIAL PRIMARY KEY,
                    round_id INTEGER NOT NULL
                        REFERENCES federated_rounds(round_id),
                    hospital_id INTEGER NOT NULL,
                    data_size_bytes BIGINT NOT NULL,
                    communication_time_seconds DOUBLE PRECISION,
                    status VARCHAR(30) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. Centralized model baseline
            cur.execute("""
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
            """)

            # 6. Local, federated and centralized model comparison
            cur.execute("""
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
            """)

            # Helpful indexes for dashboard queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_updates_round_hospital
                ON model_updates(round_id, hospital_id)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_global_models_round
                ON global_models(round_id)
            """)

        conn.commit()
        print("Federated database schema setup completed.")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
