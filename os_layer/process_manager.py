
from datetime import datetime, timedelta

from database.federated_db import get_federated_connection


def save_process_logs(results, scheduling_algorithm="Round Robin"):
    """Save scheduling results to the central OS process log."""
    conn = get_federated_connection()

    # Use one reference time so timestamps preserve the simulated offsets.
    base_time = datetime.now()

    try:
        with conn.cursor() as cur:
            for process in results:
                arrival_time = base_time + timedelta(
                    seconds=process["arrival_time"]
                )
                start_time = base_time + timedelta(
                    seconds=process["start_time"]
                )
                completion_time = base_time + timedelta(
                    seconds=process["completion_time"]
                )

                cur.execute(
                    """
                    INSERT INTO os_process_logs (
                        hospital_id,
                        process_name,
                        scheduling_algorithm,
                        priority,
                        arrival_time,
                        start_time,
                        completion_time,
                        waiting_time_seconds,
                        turnaround_time_seconds,
                        response_time_seconds,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        1,  # Demo jobs currently represent Hospital 1.
                        process["pid"],
                        scheduling_algorithm,
                        1,
                        arrival_time,
                        start_time,
                        completion_time,
                        process["waiting_time"],
                        process["turnaround_time"],
                        process["response_time"],
                        "COMPLETED",
                    ),
                )

        conn.commit()
        print(f"Saved {len(results)} process logs to PostgreSQL.")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
