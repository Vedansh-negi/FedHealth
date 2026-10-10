from os_layer.process_manager import save_process_logs
from collections import deque


def round_robin(processes, time_quantum):
    """
    Simulate Round Robin CPU scheduling.

    Each process must contain:
        pid, arrival_time, burst_time
    """
    if time_quantum <= 0:
        raise ValueError("Time quantum must be greater than zero.")

    if not processes:
        raise ValueError("At least one process is required.")

    jobs = []

    for process in processes:
        job = process.copy()

        if job["arrival_time"] < 0 or job["burst_time"] <= 0:
            raise ValueError(
                "Arrival time must be >= 0 and burst time must be > 0."
            )

        job["remaining_time"] = job["burst_time"]
        job["start_time"] = None
        job["completion_time"] = None
        jobs.append(job)

    jobs.sort(key=lambda p: (p["arrival_time"], p["pid"]))

    ready_queue = deque()
    current_time = 0
    next_process = 0
    execution_order = []

    while next_process < len(jobs) or ready_queue:

        # If no process is ready, advance to the next arrival.
        if not ready_queue and next_process < len(jobs):
            current_time = max(
                current_time,
                jobs[next_process]["arrival_time"]
            )

        # Add every process that has arrived.
        while (
            next_process < len(jobs)
            and jobs[next_process]["arrival_time"] <= current_time
        ):
            ready_queue.append(jobs[next_process])
            next_process += 1

        if not ready_queue:
            continue

        process = ready_queue.popleft()

        if process["start_time"] is None:
            process["start_time"] = current_time

        run_time = min(time_quantum, process["remaining_time"])
        start = current_time
        current_time += run_time
        process["remaining_time"] -= run_time

        execution_order.append({
            "pid": process["pid"],
            "start": start,
            "end": current_time,
        })

        # Processes arriving during this time slice join the queue
        # before the preempted process is placed at the back.
        while (
            next_process < len(jobs)
            and jobs[next_process]["arrival_time"] <= current_time
        ):
            ready_queue.append(jobs[next_process])
            next_process += 1

        if process["remaining_time"] > 0:
            ready_queue.append(process)
        else:
            process["completion_time"] = current_time

    # Calculate standard scheduling metrics.
    for process in jobs:
        process["turnaround_time"] = (
            process["completion_time"] - process["arrival_time"]
        )
        process["waiting_time"] = (
            process["turnaround_time"] - process["burst_time"]
        )
        process["response_time"] = (
            process["start_time"] - process["arrival_time"]
        )

    return jobs, execution_order


def main():
    print("=" * 55)
    print("FEDHEALTH: ROUND ROBIN CPU SCHEDULER")
    print("=" * 55)

    n = int(input("Enter number of processes: "))

    if n <= 0:
        print("Number of processes must be positive.")
        return

    processes = []

    for i in range(n):
        print(f"\nProcess P{i + 1}")
        arrival = int(input("Arrival time: "))
        burst = int(input("CPU burst time: "))

        processes.append({
            "pid": f"P{i + 1}",
            "arrival_time": arrival,
            "burst_time": burst,
        })

    quantum = int(input("\nEnter time quantum: "))

    try:
        results, execution_order = round_robin(processes, quantum)
        save_process_logs(results, scheduling_algorithm="Round Robin")
    except ValueError as error:
        print(f"Input error: {error}")
        return

    print("\nScheduling Results")
    print("-" * 85)
    print(
        f"{'PID':<8}{'AT':>8}{'BT':>8}{'ST':>8}"
        f"{'CT':>8}{'TAT':>8}{'WT':>8}{'RT':>8}"
    )
    print("-" * 85)

    for p in sorted(results, key=lambda x: x["pid"]):
        print(
            f"{p['pid']:<8}"
            f"{p['arrival_time']:>8}"
            f"{p['burst_time']:>8}"
            f"{p['start_time']:>8}"
            f"{p['completion_time']:>8}"
            f"{p['turnaround_time']:>8}"
            f"{p['waiting_time']:>8}"
            f"{p['response_time']:>8}"
        )

    avg_waiting = sum(p["waiting_time"] for p in results) / len(results)
    avg_turnaround = sum(p["turnaround_time"] for p in results) / len(results)
    avg_response = sum(p["response_time"] for p in results) / len(results)

    print("-" * 85)
    print(f"Average Waiting Time    : {avg_waiting:.2f}")
    print(f"Average Turnaround Time : {avg_turnaround:.2f}")
    print(f"Average Response Time   : {avg_response:.2f}")

    print("\nCPU Execution Timeline")
    print(" -> ".join(
        f"{item['pid']}({item['start']}-{item['end']})"
        for item in execution_order
    ))


if __name__ == "__main__":
    main()
