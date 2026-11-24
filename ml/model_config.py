
import hashlib
import json

FEATURE_COLUMNS = [
    "highbp", "highchol", "cholcheck", "bmi", "smoker", "stroke",
    "heartdiseaseorattack", "physactivity", "fruits", "veggies",
    "hvyalcoholconsump", "anyhealthcare", "nodocbccost", "genhlth",
    "menthlth", "physhlth", "diffwalk", "sex", "age", "education", "income"
]

TARGET_COLUMN = "diabetes_binary"
MODEL_VERSION = "logreg-v2"

# Actual configuration used by local_training.py
MODEL_CONFIG = {
    "model_type": "LogisticRegression",
    "optimization": "mini_batch_gradient_descent",
    "epochs": 300,
    "batch_size": 1024,
    "learning_rate": 0.40,
    "l2_strength": 0.0001,
    "random_seed": 42,
    "class_weight": "balanced",
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
}

def get_config_fingerprint():
    config_json = json.dumps(MODEL_CONFIG, sort_keys=True)
    return hashlib.sha256(
        config_json.encode("utf-8")
    ).hexdigest()

# Fingerprint of the original configuration used by rounds 2–4.
LEGACY_CONFIG_FINGERPRINT = (
    "4c85d4513b615183b51381dffb6dd7880f602d4dd0368e1fbf53e53ea5ca93a2"
)
