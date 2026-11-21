import numpy as np
import pytest

pytest.importorskip("psycopg2")

from ml.federated_learning import aggregate_models, validate_update
from ml.model_config import (
    FEATURE_COLUMNS,
    MODEL_VERSION,
    get_config_fingerprint,
)

N = len(FEATURE_COLUMNS)


def update(hospital_id, samples, weight, bias):
    return {
        "hospital_id": hospital_id,
        "sample_count": samples,
        "weights": [weight] * N,
        "bias": bias,
        "model_version": MODEL_VERSION,
        "config_fingerprint": get_config_fingerprint(),
    }


def test_fedavg_is_sample_weighted():
    weights, bias = aggregate_models([
        update(1, 100, 1.0, 1.0),
        update(2, 300, 3.0, 3.0),
    ])

    # (100*1 + 300*3) / 400 = 2.5
    assert np.allclose(weights, 2.5)
    assert bias == pytest.approx(2.5)


def test_aggregate_rejects_empty():
    with pytest.raises(ValueError):
        aggregate_models([])


def test_validate_update_accepts_good_update():
    validate_update(update(1, 10, 0.1, 0.0), get_config_fingerprint())


@pytest.mark.parametrize("bad", [
    {"sample_count": 0},
    {"bias": float("nan")},
    {"weights": [0.0] * (N - 1)},
    {"weights": [float("inf")] * N},
    {"model_version": "other"},
    {"config_fingerprint": "other"},
])
def test_validate_update_rejects_bad_updates(bad):
    result = update(1, 10, 0.1, 0.0)
    result.update(bad)

    with pytest.raises(ValueError):
        validate_update(result, get_config_fingerprint())
