
import hashlib
import json

FEATURE_COLUMNS = [
    "highbp", "highchol", "cholcheck", "bmi", "smoker", "stroke",
    "heartdiseaseorattack", "physactivity", "fruits", "veggies",
    "hvyalcoholconsump", "anyhealthcare", "nodocbccost", "genhlth",
    "menthlth", "physhlth", "diffwalk", "sex", "age", "education", "income"
]

TARGET_COLUMN = "diabetes_binary"

MODEL_CONFIG = {
    "model_type": "LogisticRegression",
    "features": FEATURE_COLUMNS,
    "target": TARGET_COLUMN,
    "scaling": {
        "bmi": "divide_by_100",
        "genhlth": "(value-1)/4",
        "menthlth": "divide_by_30",
        "physhlth": "divide_by_30",
        "age": "(value-1)/12",
        "education": "(value-1)/5",
        "income": "(value-1)/7",
    },
    "class_weight": "balanced",
    "solver": "lbfgs",
    "max_iter": 1000,
    "random_state": 42,
}

MODEL_VERSION = "logreg-v1"


def get_config_fingerprint():
    config_json = json.dumps(MODEL_CONFIG, sort_keys=True)
    return hashlib.sha256(
        config_json.encode("utf-8")
    ).hexdigest()
