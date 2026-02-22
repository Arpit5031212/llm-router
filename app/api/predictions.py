from app.repositories.SQLAlchemyPredictionRepository import SQLAlchemyPredictionRepository
from app.services.prediction_service import PredictionService
from flask import Blueprint, current_app, request, jsonify, g
import uuid


predictions_bp = Blueprint('predictions', __name__, url_prefix='/api/v1/predictions')

def get_prediction_service():
    """
    Retrieve PredictionService instance from app context.
    """

    session = g.db
    prediction_repo = SQLAlchemyPredictionRepository(session)
    adapter_factory = current_app.extensions["adapter_factory"]
    prediction_service = PredictionService(prediction_repo, adapter_factory, session)
    return prediction_service

@predictions_bp.route("/<prediction_id>", methods=["GET"])
def get_prediction(prediction_id):
    try:
        prediction_uuid = uuid.UUID(prediction_id)
    except ValueError:
        return jsonify({"error": "Invalid prediction id"}), 400

    prediction_service = get_prediction_service()
    prediction = prediction_service.prediction_repo.get_by_id(prediction_uuid)

    if not prediction:
        return jsonify({"error": "Prediction not found"}), 404

    return jsonify({
        "id": str(prediction.id),
        "model_version_id": prediction.model_version_id,
        "output": prediction.output_payload,
        "latency_ms": prediction.latency,
        "created_at": prediction.created_at.isoformat()
    })

@predictions_bp.route("", methods=["POST"])
def create_prediction():
    payload = request.get_json(silent=True)

    if not payload:
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        model_version_id = int(payload["model_version_id"])
        input_payload = payload["input"]
        comparison_id = payload.get("comparison_id")

        if comparison_id:
            comparison_id = uuid.UUID(comparison_id)

    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Invalid request payload"}), 400

    prediction_service = get_prediction_service()

    prediction = prediction_service.predict(
        user_id=1,  # temp hardcoded, auth later
        model_version_id=model_version_id,
        input_payload=input_payload,
        comparison_id=comparison_id,
    )

    return jsonify({
        "id": str(prediction.id),
        "output": prediction.output_payload,
        "latency_ms": prediction.latency,
        "created_at": prediction.created_at.isoformat()
    }), 201