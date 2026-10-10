"""
FedHealth OS process-management demonstration.

Run from the project root:
    python -m os_layer.process_execution_demo

Uses separate OS processes via ProcessPoolExecutor. One job intentionally
fails to demonstrate that the coordinator can record a failed worker while
allowing other jobs to finish. This is a demo, not a production job queue.
"""

import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

import psutil

from database.federated_db import get_federated_connection


def worker(job_id, workload, should_fail=False):
    """Worker function executed in a separate operating-system process."""
    started_at = datetime.now()
    start_perf = time.perf_counter()
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / (1024 * 1024)

    if should_fail:
        # Intentional error for the failure-isolation demonstration.
        raise RuntimeError(f"Intentional demonstration failure in {job_id}")

    total = 0
    for number in range(1, workload + 1):
        total += number * number

    elapsed = time.perf_counter() - start_perf
    completed_at = datetime.now()

    return {
        "job_id": job_id,
        "pid": os.getpid(),
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": elapsed,
        "memory_usage_mb": memory_mb,
        "result": total,
        "status": "COMPLETED",
    }


def save_job_logs(log_rows):
    """Persist worker outcomes in the existing OS log table."""
    conn = get_federated_connection()
    try:
        with conn.cursor() as cur:
            for row in log_rows:
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
                        cpu_usage,
                        memory_usage_mb,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        1,
                        row["job_id"],
                        "ProcessPoolExecutor",
                        1,
                        row["arrival_time"],
                        row["started_at"],
                        row["completed_at"],
                        row["waiting_time_seconds"],
                        row["duration_seconds"],
                        row["response_time_seconds"],
                        row.get("cpu_usage"),
                        row.get("memory_usage_mb"),
                        row["status"],
                    ),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    print("=" * 62)
    print("FEDHEALTH: OS PROCESS MANAGEMENT DEMO")
    print("=" * 62)
    print("Launching 3 independent worker processes; one job will fail intentionally.")

    jobs = [
        {"job_id": "ML-Worker-1", "workload": 250_000, "should_fail": False},
        {"job_id": "ML-Worker-2-FAIL-DEMO", "workload": 100_000, "should_fail": True},
        {"job_id": "ML-Worker-3", "workload": 300_000, "should_fail": False},
    ]

    coordinator_start = datetime.now()
    coordinator_perf = time.perf_counter()
    log_rows = []
    failures = 0

    with ProcessPoolExecutor(max_workers=3) as executor:
        future_to_job = {
            executor.submit(
                worker,
                job["job_id"],
                job["workload"],
                job["should_fail"],
            ): job
            for job in jobs
        }

        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                result = future.result()
                print(
                    f"\n{result['job_id']} COMPLETED | "
                    f"PID={result['pid']} | "
                    f"duration={result['duration_seconds']:.4f}s | "
                    f"RAM={result['memory_usage_mb']:.2f} MB | "
                    f"result={result['result']}"
                )

                log_rows.append({
                    "job_id": result["job_id"],
                    "arrival_time": coordinator_start,
                    "started_at": result["started_at"],
                    "completed_at": result["completed_at"],
                    "waiting_time_seconds": max(
                        0.0,
                        (result["started_at"] - coordinator_start).total_seconds(),
                    ),
                    "response_time_seconds": max(
                        0.0,
                        (result["started_at"] - coordinator_start).total_seconds(),
                    ),
                    "duration_seconds": result["duration_seconds"],
                    "memory_usage_mb": result["memory_usage_mb"],
                    # Per-process CPU percentage is not measured by this demo.
                    "cpu_usage": None,
                    "status": "COMPLETED",
                })
            except Exception as error:
                failures += 1
                failed_at = datetime.now()
                print(f"\n{job['job_id']} FAILED as expected: {error}")

                log_rows.append({
                    "job_id": job["job_id"],
                    "arrival_time": coordinator_start,
                    "started_at": None,
                    "completed_at": failed_at,
                    "waiting_time_seconds": max(
                        0.0, time.perf_counter() - coordinator_perf
                    ),
                    "response_time_seconds": max(
                        0.0, time.perf_counter() - coordinator_perf
                    ),
                    "duration_seconds": max(
                        0.0, time.perf_counter() - coordinator_perf
                    ),
                    "memory_usage_mb": None,
                    "cpu_usage": None,
                    "status": "FAILED",
                })

    save_job_logs(log_rows)
    completed = sum(row["status"] == "COMPLETED" for row in log_rows)

    print("\n" + "-" * 62)
    print(f"Jobs submitted : {len(jobs)}")
    print(f"Jobs completed : {completed}")
    print(f"Jobs failed    : {failures}")
    print("Worker results saved to PostgreSQL.")
    print(
        "Note: timing for failed jobs is coordinator-observed time, "
        "not an exact worker runtime."
    )
    print("Per-process CPU usage is not measured by this demonstration.")


if __name__ == "__main__":
    main()
