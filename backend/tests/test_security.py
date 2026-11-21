import pytest

pytest.importorskip("jose")
pytest.importorskip("passlib")
pytest.importorskip("fastapi")

from fastapi import HTTPException

from app.core import security


def make_token(**overrides):
    payload = {"sub": "7", "role": "doctor", "hospital_id": 2}
    payload.update(overrides)
    return security.create_access_token(payload)


def test_password_hash_roundtrip():
    hashed = security.hash_password("correct horse")
    assert hashed != "correct horse"
    assert security.verify_password("correct horse", hashed)
    assert not security.verify_password("wrong", hashed)


def test_token_roundtrip():
    user = security.user_from_payload(
        security.verify_access_token(make_token())
    )
    assert user == {"user_id": 7, "role": "doctor", "hospital_id": 2}


def test_tampered_token_is_rejected():
    token = make_token()
    assert security.verify_access_token(token[:-2] + "xx") is None


def test_payload_missing_fields_is_rejected():
    assert security.user_from_payload({"sub": "1", "role": "admin"}) is None
    assert security.user_from_payload(None) is None


def test_require_roles():
    checker = security.require_roles("admin")

    assert checker(current_user={"role": "admin"}) == {"role": "admin"}

    with pytest.raises(HTTPException) as exc:
        checker(current_user={"role": "nurse"})
    assert exc.value.status_code == 403


class FakeRequest:
    def __init__(self, method):
        self.method = method


def test_method_roles():
    checker = security.method_roles(
        read=("nurse", "admin"), write=("admin",), delete=("admin",)
    )
    nurse = {"role": "nurse"}

    assert checker(FakeRequest("GET"), nurse) == nurse

    for method in ("POST", "PUT", "DELETE"):
        with pytest.raises(HTTPException) as exc:
            checker(FakeRequest(method), nurse)
        assert exc.value.status_code == 403


def test_hospital_scope_blocks_other_hospitals():
    user = {"user_id": 1, "role": "admin", "hospital_id": 1}

    assert security.hospital_scope(hospital_id=1, current_user=user) == user

    with pytest.raises(HTTPException) as exc:
        security.hospital_scope(hospital_id=2, current_user=user)
    assert exc.value.status_code == 403
