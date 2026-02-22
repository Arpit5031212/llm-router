from typing import Any, Dict
import random

from app.adapters.base import BaseModelAdapter

class DummyAdapter(BaseModelAdapter):
    def predict(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        prompt = input_payload.get("prompt")
        return {
            "provider": "dummy",
            "echo": prompt,
            "analysis": f"Processed {len(prompt)} characters.",
            "confidence": round(random.uniform(0.7, 0.99), 2)
        }