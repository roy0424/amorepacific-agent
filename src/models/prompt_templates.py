"""
Prompt template overrides saved from the UI.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from src.core.database import Base


class PromptTemplate(Base):
    """Stored prompt template overrides for reuse."""
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True)
    template_key = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
