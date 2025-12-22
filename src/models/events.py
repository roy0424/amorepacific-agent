"""
이벤트 관련 ORM 모델
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Numeric, Text, ARRAY
from sqlalchemy.orm import relationship
from src.core.database import Base


class RankingEvent(Base):
    """랭킹 변동 이벤트"""
    __tablename__ = 'ranking_events'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('amazon_products.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('amazon_categories.id'), nullable=False)

    # 이벤트 타입
    event_type = Column(String(50), nullable=False)  # RANK_SURGE, RANK_DROP, PRICE_CHANGE, etc.
    severity = Column(String(20), nullable=False)    # critical, high, medium, low

    # 랭킹 변동
    prev_rank = Column(Integer)
    curr_rank = Column(Integer)
    rank_change = Column(Integer)  # curr - prev (음수면 상승)
    rank_change_pct = Column(Float)

    # 가격 변동
    prev_price = Column(Numeric(10, 2))
    curr_price = Column(Numeric(10, 2))
    price_change_pct = Column(Float)

    # 리뷰 변동
    prev_review_count = Column(Integer)
    curr_review_count = Column(Integer)
    review_change = Column(Integer)

    # 시간 정보
    detected_at = Column(DateTime(timezone=True), nullable=False)
    time_window_start = Column(DateTime(timezone=True))
    time_window_end = Column(DateTime(timezone=True))

    # 처리 상태
    context_collected = Column(Boolean, default=False)
    insight_generated = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    product = relationship("AmazonProduct", back_populates="events")
    category = relationship("AmazonCategory")
    social_context = relationship("EventContextSocial", back_populates="event", cascade="all, delete-orphan")
    review_context = relationship("EventContextReview", back_populates="event", cascade="all, delete-orphan")
    competitor_context = relationship("EventContextCompetitor", back_populates="event", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'event_type': self.event_type,
            'severity': self.severity,
            'rank_change': self.rank_change,
            'rank_change_pct': self.rank_change_pct,
            'price_change_pct': self.price_change_pct,
            'review_change': self.review_change,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'context_collected': self.context_collected,
            'insight_generated': self.insight_generated,
        }

    def __repr__(self):
        return f"<RankingEvent(id={self.id}, type={self.event_type}, severity={self.severity})>"


class EventContextSocial(Base):
    """이벤트 원인 데이터: 소셜미디어"""
    __tablename__ = 'event_context_social'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('ranking_events.id', ondelete='CASCADE'), nullable=False, index=True)

    platform = Column(String(20), nullable=False)  # youtube, tiktok, instagram
    content_id = Column(String(255), nullable=False)
    author = Column(String(255))
    text = Column(Text)
    hashtags = Column(Text)  # SQLite doesn't support ARRAY, use comma-separated string

    # 메트릭
    view_count = Column(Integer)
    like_count = Column(Integer)
    comment_count = Column(Integer)
    share_count = Column(Integer)
    engagement_score = Column(Integer)

    posted_at = Column(DateTime(timezone=True))
    collected_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # 바이럴 여부
    is_viral = Column(Boolean, default=False)

    # Relationships
    event = relationship("RankingEvent", back_populates="social_context")

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'platform': self.platform,
            'content_id': self.content_id,
            'author': self.author,
            'engagement_score': self.engagement_score,
            'is_viral': self.is_viral,
        }

    def __repr__(self):
        return f"<EventContextSocial(platform={self.platform}, engagement={self.engagement_score})>"


class EventContextReview(Base):
    """이벤트 원인 데이터: 리뷰"""
    __tablename__ = 'event_context_reviews'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('ranking_events.id', ondelete='CASCADE'), nullable=False, index=True)

    review_id = Column(String(255))
    reviewer_name = Column(String(255))
    rating = Column(Integer)
    verified_purchase = Column(Boolean)
    review_title = Column(Text)
    review_text = Column(Text)
    helpful_count = Column(Integer)
    review_date = Column(DateTime(timezone=True))
    collected_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # 감성 분석 (선택)
    sentiment = Column(String(20))  # positive, negative, neutral
    sentiment_score = Column(Float)

    # Relationships
    event = relationship("RankingEvent", back_populates="review_context")

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'rating': self.rating,
            'sentiment': self.sentiment,
            'review_date': self.review_date.isoformat() if self.review_date else None,
        }

    def __repr__(self):
        return f"<EventContextReview(rating={self.rating}, sentiment={self.sentiment})>"


class EventContextCompetitor(Base):
    """이벤트 원인 데이터: 경쟁사"""
    __tablename__ = 'event_context_competitors'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('ranking_events.id', ondelete='CASCADE'), nullable=False, index=True)

    competitor_product_id = Column(Integer, ForeignKey('amazon_products.id'))
    competitor_rank = Column(Integer)
    competitor_price = Column(Numeric(10, 2))
    competitor_rating = Column(Numeric(3, 2))
    rank_change = Column(Integer)
    price_change_pct = Column(Float)

    collected_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    event = relationship("RankingEvent", back_populates="competitor_context")
    competitor_product = relationship("AmazonProduct")

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'competitor_rank': self.competitor_rank,
            'competitor_price': float(self.competitor_price) if self.competitor_price else None,
        }

    def __repr__(self):
        return f"<EventContextCompetitor(rank={self.competitor_rank})>"


class EventInsight(Base):
    """LLM이 생성한 이벤트 인사이트"""
    __tablename__ = 'event_insights'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('ranking_events.id', ondelete='CASCADE'), nullable=False, index=True)

    # LLM 생성 인사이트
    summary = Column(Text, nullable=False)  # 요약 (1-2 문장)
    analysis = Column(Text, nullable=False)  # 상세 분석
    likely_causes = Column(Text)  # 주요 원인 (JSON 배열)
    recommendations = Column(Text)  # 권장 액션 (JSON 배열)

    # 유사 이벤트 (RAG 검색 결과)
    similar_events = Column(Text)  # 유사 이벤트 ID 목록 (JSON 배열)
    similarity_scores = Column(Text)  # 유사도 점수 (JSON 배열)

    # 메타데이터
    llm_model = Column(String(50))  # 사용한 LLM 모델
    prompt_version = Column(String(20))  # 프롬프트 버전
    confidence_score = Column(Float)  # 인사이트 신뢰도 (0-1)

    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    event = relationship("RankingEvent", backref="insights")

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'summary': self.summary,
            'analysis': self.analysis,
            'llm_model': self.llm_model,
            'confidence_score': self.confidence_score,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
        }

    def __repr__(self):
        return f"<EventInsight(event_id={self.event_id}, model={self.llm_model})>"
