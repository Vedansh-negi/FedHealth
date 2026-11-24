"""Safely extend the existing OS process log table."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import psycopg2
from config.database import connection_kwargs


def main():
    connection = psycopg2.connect(
        **connection_kwargs("federated_db")
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE os_process_logs
                    ADD COLUMN IF NOT EXISTS scheduling_unit
                        VARCHAR(30) NOT NULL DEFAULT 'seconds',
                    ADD COLUMN IF NOT EXISTS burst_time_units
                        DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS waiting_time_units
                        DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS turnaround_time_units
                        DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS response_time_units
                        DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS time_quantum_units
                        DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS created_at
                        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_os_process_logs_created_at
                ON os_process_logs (created_at DESC);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_os_process_logs_hospital_status
                ON os_process_logs (hospital_id, status);
            """)

        connection.commit()
        print("OS process-log migration completed successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
