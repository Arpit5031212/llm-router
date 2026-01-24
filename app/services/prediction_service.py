import hashlib
import json
import time
from typing import Any, Dict
import uuid
from app.models.models import Prediction
from app.repositories.prediction_repo import PredictionRepository
from app.adapters.base import ModelAdapterFactory
from sqlalchemy.orm import Session

class PredictionService:
    def __init__(
        self, 
        prediction_repo: PredictionRepository, 
        adapter_factory: ModelAdapterFactory, 
        session: Session
    ):
        self.prediction_repo = prediction_repo
        self.adapter_factory = adapter_factory
        self.session = session

    def predict(
        self, 
        *, 
        user_id: int, 
        model_version_id: int, 
        input_payload: Dict[str, Any], 
        comparison_id: uuid.UUID | None = None
    ) -> Prediction:
        input_hash = self._hash_input(input_payload)
        
        existing = self.prediction_repo.find_latest_by_hash(input_hash=input_hash,
                                                            model_version_id=model_version_id)

        if existing:
            return existing
        try:
            adapter = self.adapter_factory.get_adapter(model_version_id)
            start = time.perf_counter()
            output_prediction = adapter.predict(input_payload)
            latency_ms = int((time.perf_counter() - start) * 1000)
            prediction = Prediction(
                id=uuid.uuid4(),
                model_version_id=model_version_id,
                user_id=user_id,
                comparison_id=comparison_id,
                input_hash=input_hash,
                input_payload=input_payload,
                output_payload=output_prediction,
                latency=latency_ms
            )
            self.prediction_repo.create(prediction)
            self.session.commit()
            return prediction
        except Exception:
            self.session.rollback()
            raise

    def _hash_input(self, input_payload: Dict[str, Any]) -> str:
        serialized = json.dumps(input_payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()