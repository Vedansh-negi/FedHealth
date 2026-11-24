"""Create the PostgreSQL tables used by FedHealth's OS integration.

Run from the project root:
    python3 scripts/init_os_schema.py

This migration is safe to run more than once: it uses CREATE TABLE IF NOT EXISTS
and does not delete or modify existing hospital or federated-learning data.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.database import connection_kwargs
import psycopg2


def main():
    connection = psycopg2.connect(**connection_kwargs("federated_db"))

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS os_process_logs (
                    process_log_id BIGSERIAL PRIMARY KEY,
                    hospital_id INTEGER NOT NULL DEFAULT 1,
                    process_name VARCHAR(150) NOT NULL,
                    scheduling_algorithm VARCHAR(40) NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 1,
                    arrival_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    start_time TIMESTAMP,
                    completion_time TIMESTAMP,
                    waiting_time_seconds DOUBLE PRECISION,
                    turnaround_time_seconds DOUBLE PRECISION,
                    response_time_seconds DOUBLE PRECISION,
                    cpu_usage DOUBLE PRECISION,
                    memory_usage_mb DOUBLE PRECISION,
                    status VARCHAR(30) NOT NULL DEFAULT 'QUEUED',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Additive migration for Round Robin training-job metrics.
            # Existing OS/demo records remain unchanged.
            cursor.execute(
                """
                ALTER TABLE os_process_logs
                    ADD COLUMN IF NOT EXISTS scheduling_unit VARCHAR(30) NOT NULL DEFAULT 'seconds',
                    ADD COLUMN IF NOT EXISTS burst_time_units DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS waiting_time_units DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS turnaround_time_units DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS response_time_units DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS time_quantum_units DOUBLE PRECISION
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_os_process_logs_created_at
                ON os_process_logs (created_at DESC)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_os_process_logs_hospital_status
                ON os_process_logs (hospital_id, status)
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS resource_monitor_logs (
                    snapshot_id BIGSERIAL PRIMARY KEY,
                    cpu_percent DECIMAL(6,2) NOT NULL,
                    memory_percent DECIMAL(6,2) NOT NULL,
                    system_memory_used_mb DECIMAL(12,2),
                    process_memory_mb DECIMAL(12,2),
                    available_memory_mb DECIMAL(12,2),
                    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_resource_monitor_recorded_at
                ON resource_monitor_logs (recorded_at DESC)
                """
            )

        connection.commit()
        print("FedHealth OS schema initialized successfully.")
        print("Tables ready: os_process_logs, resource_monitor_logs")
        print("Round Robin scheduler metric columns verified.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
