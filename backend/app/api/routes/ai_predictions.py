
import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor, Json

from database.hospital_db import get_hospital_connection
from database.federated_db import get_federated_connection
from ml.model_config import FEATURE_COLUMNS, get_config_fingerprint


router = APIRouter(
    prefix="/api/ai-predictions",
    tags=["AI Predictions"]
)


class PredictionInput(BaseModel):
    patient_id: int = Field(..., gt=0)

    highbp: int = Field(..., ge=0, le=1)
    highchol: int = Field(..., ge=0, le=1)
    cholcheck: int = Field(..., ge=0, le=1)
    bmi: float = Field(..., gt=0)

    smoker: int = Field(..., ge=0, le=1)
    stroke: int = Field(..., ge=0, le=1)
    heartdiseaseorattack: int = Field(..., ge=0, le=1)
    physactivity: int = Field(..., ge=0, le=1)
    fruits: int = Field(..., ge=0, le=1)
    veggies: int = Field(..., ge=0, le=1)
    hvyalcoholconsump: int = Field(..., ge=0, le=1)
    anyhealthcare: int = Field(..., ge=0, le=1)
    nodocbccost: int = Field(..., ge=0, le=1)

    genhlth: int = Field(..., ge=1, le=5)
    menthlth: int = Field(..., ge=0, le=30)
    physhlth: int = Field(..., ge=0, le=30)
    diffwalk: int = Field(..., ge=0, le=1)
    sex: int = Field(..., ge=0, le=1)
    age: int = Field(..., ge=1, le=13)
    education: int = Field(..., ge=1, le=6)
    income: int = Field(..., ge=1, le=8)


def transform_features(data: PredictionInput):
    features = data.model_dump()

    features.pop("patient_id")

    # Apply the same scaling used during model training
    features["bmi"] = features["bmi"] / 100
    features["genhlth"] = (features["genhlth"] - 1) / 4
    features["menthlth"] = features["menthlth"] / 30
    features["physhlth"] = features["physhlth"] / 30
    features["age"] = (features["age"] - 1) / 12
    features["education"] = (features["education"] - 1) / 5
    features["income"] = (features["income"] - 1) / 7

    # Maintain the exact feature order used during training
    return np.array(
        [features[column] for column in FEATURE_COLUMNS],
        dtype=float
    )


def sigmoid(value):
    return 1 / (1 + np.exp(-value))


@router.post("/")
def predict_diabetes(
    data: PredictionInput,
    hospital_id: int = Query(1, ge=1, le=3)
):
    hospital_connection = None
    federated_connection = None

    try:
        # 1. Verify patient exists in selected hospital
        hospital_connection = get_hospital_connection(hospital_id)

        with hospital_connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                SELECT patient_id
                FROM patients
                WHERE patient_id = %s
                """,
                (data.patient_id,)
            )

            patient = cursor.fetchone()

        if not patient:
            raise HTTPException(
                status_code=404,
                detail="Patient not found in selected hospital"
            )

        # 2. Fetch latest completed federated model
        federated_connection = get_federated_connection()

        with federated_connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    gm.weights,
                    gm.bias,
                    gm.model_version
                FROM global_models gm
                JOIN federated_rounds fr
                    ON gm.round_id = fr.round_id
                WHERE fr.status = 'COMPLETED'
                    AND gm.config_fingerprint = %s
                ORDER BY
                    fr.round_number DESC,
                    gm.global_model_id DESC
                LIMIT 1
                """,
                (get_config_fingerprint(),)
            )

            model = cursor.fetchone()

        if model is None:
            raise HTTPException(
                status_code=404,
                detail="No completed federated model found. Train the model first."
            )

        # FIX: Default psycopg2 cursor returns a tuple
        weights = np.asarray(model[0], dtype=float)
        bias = float(model[1])
        model_version = model[2]

        # 3. Transform input features
        input_features = transform_features(data)

        # 4. Calculate prediction probability
        logit = np.dot(weights, input_features) + bias
        probability = float(sigmoid(logit))

        # Binary prediction
        prediction = 1 if probability >= 0.5 else 0

        result = {
            "patient_id": data.patient_id,
            "hospital_id": hospital_id,
            "prediction": prediction,
            "prediction_label": (
                "Diabetes risk detected"
                if prediction == 1
                else "No diabetes risk detected"
            ),
            "probability": round(probability, 5),
            "model_name": "Federated Logistic Regression",
            "model_version": model_version
        }

        # 5. Save prediction in hospital database
        with hospital_connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                INSERT INTO ai_predictions (
                    patient_id,
                    model_name,
                    model_version,
                    prediction_result,
                    confidence_score
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING prediction_id, created_at
                """,
                (
                    data.patient_id,
                    "Federated Logistic Regression",
                    model_version,
                    Json(result),
                    probability
                )
            )

            saved_prediction = cursor.fetchone()

        hospital_connection.commit()

        result["prediction_id"] = saved_prediction["prediction_id"]
        result["created_at"] = saved_prediction["created_at"]

        return result

    except HTTPException:
        raise

    except Exception as error:
        if hospital_connection:
            hospital_connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(error)}"
        )

    finally:
        if hospital_connection:
            hospital_connection.close()

        if federated_connection:
            federated_connection.close()


# Get all predictions
@router.get("/")
def get_predictions(
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = get_hospital_connection(hospital_id)

    try:
        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                SELECT *
                FROM ai_predictions
                ORDER BY created_at DESC
                """
            )

            return cursor.fetchall()

    finally:
        connection.close()


# Get prediction by ID
@router.get("/{prediction_id}")
def get_prediction(
    prediction_id: int,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = get_hospital_connection(hospital_id)

    try:
        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                SELECT *
                FROM ai_predictions
                WHERE prediction_id = %s
                """,
                (prediction_id,)
            )

            prediction = cursor.fetchone()

            if not prediction:
                raise HTTPException(
                    status_code=404,
                    detail="Prediction not found"
                )

            return prediction

    finally:
        connection.close()


# Get predictions for a patient
@router.get("/patient/{patient_id}")
def get_patient_predictions(
    patient_id: int,
    hospital_id: int = Query(1, ge=1, le=3)
):
    connection = get_hospital_connection(hospital_id)

    try:
        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                SELECT *
                FROM ai_predictions
                WHERE patient_id = %s
                ORDER BY created_at DESC
                """,
                (patient_id,)
            )

            return cursor.fetchall()

    finally:
        connection.close()
