import uuid
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from sqlalchemy import DateTime, ForeignKey, String, String, BIGINT, UUID, Index, Integer, func, text
from sqlalchemy.dialects.postgresql import JSONB

import datetime
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

class LLMModel(Base):
    __tablename__= 'models'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)

class ModelVersion(Base):
    __tablename__= 'model_versions'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(ForeignKey('models.id'), nullable=False)
    version: Mapped[str] = mapped_column(String(64))
    config_json: Mapped[JSONB] = mapped_column(JSONB)
    is_acive: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)

class Comparison(Base):
    __tablename__ = 'comparisons'
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    input_payload: Mapped[JSONB] = mapped_column(JSONB)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    preferred_prediction_id: Mapped[UUID] = mapped_column(ForeignKey('predictions.id'), nullable=True)
    
    __table_args__ = (
        Index('idx_comparisons_user_created', 'user_id', text('created_at DESC')),
    )
    
class Prediction(Base):
    __tablename__ = 'predictions'
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version_id: Mapped[int] = mapped_column(ForeignKey('model_versions.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    comparison_id: Mapped[UUID] = mapped_column(ForeignKey('comparisons.id'), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(255))
    input_payload: Mapped[JSONB] = mapped_column(JSONB)
    output_payload: Mapped[JSONB] = mapped_column(JSONB)
    latency: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_predictions_comparison', text('comparison_id ASC NULLS LAST')),
        Index('idx_predictions_dedupe', text('input_hash ASC NULLS LAST'), text('model_version_id ASC NULLS LAST'), text('created_at DESC NULLS FIRST')),
        Index('idx_predictions_input_hash', text('input_hash ASC NULLS LAST')),
        Index('idx_predictions_model_version_created', text('model_version_id ASC NULLS LAST'), text('created_at DESC NULLS FIRST')),
        Index('idx_predictions_user_created', text('user_id ASC NULLS LAST'), text('created_at DESC NULLS FIRST')),
    )