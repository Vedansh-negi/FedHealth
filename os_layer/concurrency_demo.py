"""
FedHealth OS demonstration: race condition and synchronization.

Run from the project root:
    python -m os_layer.concurrency_demo

This is a teaching demonstration using threads and shared memory.
It does not modify the database or any existing FedHealth modules.
"""

import threading
import time

THREAD_COUNT = 4
INCREMENTS_PER_THREAD = 2_000


def run_without_lock():
    """Intentionally unsafe shared-counter update to demonstrate a race."""
    shared = {"counter": 0}

    def worker():
        for _ in range(INCREMENTS_PER_THREAD):
            # Deliberately separate the read and write so threads can interleave.
            current = shared["counter"]
            time.sleep(0)
            shared["counter"] = current + 1

    threads = [
        threading.Thread(target=worker, name=f"unsafe-{i + 1}")
        for i in range(THREAD_COUNT)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return shared["counter"]


def run_with_lock():
    """Protect the shared-counter critical section using a mutex lock."""
    shared = {"counter": 0}
    lock = threading.Lock()

    def worker():
        for _ in range(INCREMENTS_PER_THREAD):
            with lock:
                current = shared["counter"]
                time.sleep(0)
                shared["counter"] = current + 1

    threads = [
        threading.Thread(target=worker, name=f"safe-{i + 1}")
        for i in range(THREAD_COUNT)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return shared["counter"]


def main():
    expected = THREAD_COUNT * INCREMENTS_PER_THREAD

    print("=" * 60)
    print("FEDHEALTH: OS CONCURRENCY AND SYNCHRONIZATION DEMO")
    print("=" * 60)
    print(f"Threads: {THREAD_COUNT}")
    print(f"Increments per thread: {INCREMENTS_PER_THREAD}")
    print(f"Expected final counter: {expected}")

    unsafe_result = run_without_lock()
    print("\n1. WITHOUT LOCK (race-condition demonstration)")
    print(f"Actual final counter:   {unsafe_result}")
    print(f"Lost updates:           {expected - unsafe_result}")

    safe_result = run_with_lock()
    print("\n2. WITH LOCK (synchronized critical section)")
    print(f"Actual final counter:   {safe_result}")
    print(f"Lost updates:           {expected - safe_result}")

    if safe_result == expected:
        print("\nPASS: lock protected the shared counter.")
    else:
        print("\nFAIL: synchronized result differed from expected value.")

    print(
        "\nNote: the exact unsafe result can vary by run and Python/runtime. "
        "The unsafe example intentionally yields between read and write."
    )


if __name__ == "__main__":
    main()
