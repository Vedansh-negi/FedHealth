import threading

import pytest
from fastapi import BackgroundTasks, HTTPException

pytest.importorskip("fastapi")
pytest.importorskip("psycopg2")

from app.api.routes import federated


def test_second_training_request_returns_409_when_lock_is_held(monkeypatch):
    lock = threading.Lock()
    lock.acquire()

    monkeypatch.setattr(federated, "_training_lock", lock)

    with pytest.raises(HTTPException) as exc:
        federated.start_federated_round(
            BackgroundTasks(),
            current_user={
                "user_id": 1,
                "hospital_id": 1,
            },
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "A training round is already in progress"

    lock.release()
