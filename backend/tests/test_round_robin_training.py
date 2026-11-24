from os_layer.scheduler import round_robin


def test_round_robin_interleaves_hospital_training_tasks():
    jobs = [
        {"pid": "H1", "hospital_id": 1, "arrival_time": 0, "burst_time": 3},
        {"pid": "H2", "hospital_id": 2, "arrival_time": 0, "burst_time": 2},
        {"pid": "H3", "hospital_id": 3, "arrival_time": 0, "burst_time": 2},
    ]
    completed, timeline = round_robin(jobs, time_quantum=1)

    assert [item["pid"] for item in timeline[:6]] == [
        "H1", "H2", "H3", "H1", "H2", "H3"
    ]
    assert {item["pid"] for item in completed} == {"H1", "H2", "H3"}
    assert all(item["completion_time"] is not None for item in completed)
