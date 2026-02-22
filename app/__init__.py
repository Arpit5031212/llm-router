from app.adapters.factory import ModelAdapterFactory
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import g

from app.api.predictions import predictions_bp
from app.repositories.SQLAlchemyPredictionRepository import SQLAlchemyPredictionRepository
from app.services.prediction_service import PredictionService

def create_app():
    app = Flask(__name__)

    # 1️⃣ Create engine
    engine = create_engine(
        "postgresql://postgres:admin@localhost:5432/llm_router",
        pool_pre_ping=True,
        echo=False
    )

    # 2️⃣ Create session factory
    SessionLocal = sessionmaker(bind=engine)

    # 3️⃣ Create session (for now, simple version)
    session = SessionLocal()

    @app.before_request
    def create_request_session():
        g.db = app.extensions["session_factory"]()
    
    @app.teardown_request
    def shutdown_session(exception=None):
        db = g.get("db")
        if not db:
            return None
        try:
            if exception:
                db.rollback()
            else:
                db.commit()
            db.close()
        except Exception as e:
            app.logger.error(f"Error closing session: {e}")
            db.rollback()
        finally:
            db.close()

    # 4️⃣ Create repository
    prediction_repo = SQLAlchemyPredictionRepository(session)

    # 5️⃣ Create adapter factory
    adapter_factory = ModelAdapterFactory()

    # 6️⃣ Create service
    prediction_service = PredictionService(
        prediction_repo=prediction_repo,
        adapter_factory=adapter_factory,
        session=session,
    )

    # 7️⃣ Store in app context
    app.extensions["prediction_service"] = prediction_service
    app.extensions["adapter_factory"] = adapter_factory
    app.extensions["session_factory"] = SessionLocal

    # 8️⃣ Register blueprints
    app.register_blueprint(predictions_bp)

    return app