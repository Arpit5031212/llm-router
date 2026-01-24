from typing import Optional, List
from app.models.models import Prediction
from app.repositories.prediction_repo import PredictionRepository
from sqlalchemy import select
from sqlalchemy.orm import Session
import uuid

class SQLAlchemyPredictionRepository(PredictionRepository):
    def __init__(self, session: Session):
        self.session = session

    def create(self, prediction: Prediction) -> Prediction:
        self.session.add(prediction)
        # self.session.commit()
        self.session.flush()
        return prediction

    def get_by_id(self, prediction_id: uuid.UUID) -> Optional[Prediction]:
        selection_query = select(Prediction).where(Prediction.id == prediction_id)
        return self.session.execute(selection_query).scalar_one_or_none()
    
    def find_latest_by_hash(self, input_hash: str, model_version_id: int) -> Optional[Prediction]:
        selection_query = (
            select(Prediction).where(Prediction.input_hash == input_hash,
                                     Prediction.model_version_id == model_version_id)
            .order_by(Prediction.created_at.desc())
            .limit(1)
        )
        return self.session.execute(selection_query).scalar_one_or_none()
    
    def find_by_comparison(self, comparison_id: uuid.UUID) -> List[Prediction]:
        selection_query = (
            select(Prediction)
            .where(Prediction.comparison_id == comparison_id)
            .order_by(Prediction.created_at.asc())
        )
        result = list(self.session.execute(selection_query).scalars().all())
        return result

        
    