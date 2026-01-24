from abc import ABC, abstractmethod
class PredictionRepository(ABC):
    
    @abstractmethod
    def create(self, prediction) -> None:
        """Persist prediction"""
        
    @abstractmethod
    def get_by_id(self, prediction_id):
        """Return Prediction or None"""
        
    @abstractmethod
    def find_latest_by_hash(self, input_hash, model_version_id):
        """Return latest Prediction or None"""
        
    @abstractmethod
    def find_by_comparison(self, comparison_id):
        """Return list[Prediction]"""

