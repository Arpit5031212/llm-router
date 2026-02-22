from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseModelAdapter(ABC):
    @abstractmethod
    def predict(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute inference on input payload and return normalized output"""
        pass