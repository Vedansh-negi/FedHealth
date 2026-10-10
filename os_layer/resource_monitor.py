
import os
import psutil

from database.federated_db import get_federated_connection


def get_resource_usage():
    """Measure current system and FedHealth process resources."""
    memory = psutil.virtual_memory()
    process = psutil.Process(os.getpid())

    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": memory.percent,
        "system_memory_used_mb": memory.used / (1024 * 1024),
        "process_memory_mb": process.memory_info().rss / (1024 * 1024),
        "available_memory_mb": memory.available / (1024 * 1024),
    }


def save_resource_usage(usage):
    """Create the resource log table if needed and save one snapshot."""
    conn = get_federated_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS resource_monitor_logs (
                    snapshot_id SERIAL PRIMARY KEY,
                    cpu_percent DECIMAL(6,2) NOT NULL,
                    memory_percent DECIMAL(6,2) NOT NULL,
                    system_memory_used_mb DECIMAL(12,2),
                    process_memory_mb DECIMAL(12,2),
                    available_memory_mb DECIMAL(12,2),
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cur.execute(
                """
                INSERT INTO resource_monitor_logs (
                    cpu_percent,
                    memory_percent,
                    system_memory_used_mb,
                    process_memory_mb,
                    available_memory_mb
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    usage["cpu_percent"],
                    usage["memory_percent"],
                    usage["system_memory_used_mb"],
                    usage["process_memory_mb"],
                    usage["available_memory_mb"],
                ),
            )

        conn.commit()
        print("Resource snapshot saved to PostgreSQL.")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    usage = get_resource_usage()

    print("\nFedHealth Resource Monitor")
    print("-" * 40)
    print(f"System CPU usage:       {usage['cpu_percent']:.2f}%")
    print(f"System memory usage:    {usage['memory_percent']:.2f}%")
    print(f"System memory used:     {usage['system_memory_used_mb']:.2f} MB")
    print(f"FedHealth process RAM:  {usage['process_memory_mb']:.2f} MB")
    print(f"Available system RAM:   {usage['available_memory_mb']:.2f} MB")

    save_resource_usage(usage)
