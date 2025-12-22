"""
시나리오 테스트용 더미 데이터 모델
실데이터와 분리된 테이블에 저장한다.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.sql import func
from src.core.database import Base


class ScenarioCategory(Base):
    """시나리오 카테고리"""
    __tablename__ = "scenario_categories"

    id = Column(Integer, primary_key=True)
    category_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScenarioProduct(Base):
    """시나리오 제품"""
    __tablename__ = "scenario_products"

    id = Column(Integer, primary_key=True)
    asin = Column(String(20), unique=True, nullable=False, index=True)
    product_name = Column(Text, nullable=False)
    brand_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScenarioRanking(Base):
    """시나리오 랭킹 히스토리"""
    __tablename__ = "scenario_rankings"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("scenario_products.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("scenario_categories.id"), nullable=False, index=True)
    rank = Column(Integer, nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=True)
    rating = Column(Numeric(3, 2), nullable=True)
    review_count = Column(Integer, nullable=True)
    is_prime = Column(Boolean, default=False)
    stock_status = Column(String(50), nullable=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ScenarioRankingEvent(Base):
    """시나리오 랭킹 이벤트"""
    __tablename__ = "scenario_ranking_events"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("scenario_products.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("scenario_categories.id"), nullable=False)

    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)

    prev_rank = Column(Integer)
    curr_rank = Column(Integer)
    rank_change = Column(Integer)
    rank_change_pct = Column(Float)

    prev_price = Column(Numeric(10, 2))
    curr_price = Column(Numeric(10, 2))
    price_change_pct = Column(Float)

    prev_review_count = Column(Integer)
    curr_review_count = Column(Integer)
    review_change = Column(Integer)

    detected_at = Column(DateTime(timezone=True), nullable=False)
    time_window_start = Column(DateTime(timezone=True))
    time_window_end = Column(DateTime(timezone=True))

    context_collected = Column(Boolean, default=False)
    insight_generated = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
