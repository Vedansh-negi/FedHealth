
from datetime import datetime, timedelta

from database.federated_db import get_federated_connection


def save_process_logs(
    results,
    scheduling_algorithm="Round Robin",
    scheduling_unit="seconds",
    time_quantum=None,
):
    """
    Persist scheduler results in the central OS process log.

    Supports:
    - seconds: standalone OS scheduling demonstrations
    - mini_batches: federated hospital training scheduling
    """
    if scheduling_unit not in ("seconds", "mini_batches"):
        raise ValueError(
            "scheduling_unit must be 'seconds' or 'mini_batches'."
        )

    if not results:
        return

    conn = get_federated_connection()
    base_time = datetime.now()

    try:
        with conn.cursor() as cur:
            for process in results:
                if scheduling_unit == "seconds":
                    arrival_time = base_time + timedelta(
                        seconds=process["arrival_time"]
                    )
                    start_time = base_time + timedelta(
                        seconds=process["start_time"]
                    )
                    completion_time = base_time + timedelta(
                        seconds=process["completion_time"]
                    )

                    waiting_seconds = process.get("waiting_time")
                    turnaround_seconds = process.get("turnaround_time")
                    response_seconds = process.get("response_time")

                else:
                    # These timestamps identify the recorded run.
                    # Scheduler metrics are stored in their declared unit.
                    arrival_time = base_time
                    start_time = base_time
                    completion_time = base_time

                    waiting_seconds = None
                    turnaround_seconds = None
                    response_seconds = None

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
                        status,
                        scheduling_unit,
                        burst_time_units,
                        waiting_time_units,
                        turnaround_time_units,
                        response_time_units,
                        time_quantum_units
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        process.get("hospital_id", 1),
                        process["pid"],
                        scheduling_algorithm,
                        process.get("priority", 1),
                        arrival_time,
                        start_time,
                        completion_time,
                        waiting_seconds,
                        turnaround_seconds,
                        response_seconds,
                        "COMPLETED",
                        scheduling_unit,
                        process.get("burst_time"),
                        process.get("waiting_time"),
                        process.get("turnaround_time"),
                        process.get("response_time"),
                        time_quantum,
                    ),
                )

        conn.commit()
        print(f"Saved {len(results)} process logs to PostgreSQL.")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

