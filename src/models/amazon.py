"""
아마존 데이터 모델
카테고리, 제품, 랭킹 히스토리, 스케줄 로그
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Index, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base


class AmazonCategory(Base):
    """아마존 카테고리 테이블"""
    __tablename__ = "amazon_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(100), nullable=False)
    category_url = Column(Text, nullable=False)
    parent_category_id = Column(Integer, ForeignKey("amazon_categories.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    parent = relationship("AmazonCategory", remote_side=[id], backref="subcategories")
    rankings = relationship("AmazonRanking", back_populates="category")

    def __repr__(self):
        return f"<AmazonCategory(name='{self.category_name}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "category_name": self.category_name,
            "category_url": self.category_url,
            "parent_category_id": self.parent_category_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AmazonProduct(Base):
    """아마존 제품 마스터 테이블"""
    __tablename__ = "amazon_products"

    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(20), unique=True, nullable=False, index=True)
    product_name = Column(Text, nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    main_image_url = Column(Text, nullable=True)
    product_url = Column(Text, nullable=True)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)

    # 관계
    brand = relationship("Brand", backref="amazon_products")
    rankings = relationship("AmazonRanking", back_populates="product")
    events = relationship("RankingEvent", back_populates="product")

    def __repr__(self):
        return f"<AmazonProduct(asin='{self.asin}', name='{self.product_name[:50]}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "asin": self.asin,
            "product_name": self.product_name,
            "brand_id": self.brand_id,
            "main_image_url": self.main_image_url,
            "product_url": self.product_url,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "is_active": self.is_active
        }


class AmazonRanking(Base):
    """아마존 랭킹 히스토리 테이블 (시계열 데이터)"""
    __tablename__ = "amazon_rankings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("amazon_products.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("amazon_categories.id"), nullable=False, index=True)
    rank = Column(Integer, nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=True)  # 가격 (소수점 2자리)
    rating = Column(Numeric(3, 2), nullable=True)  # 평점 (예: 4.5)
    review_count = Column(Integer, nullable=True)
    is_prime = Column(Boolean, default=False)
    stock_status = Column(String(50), nullable=True)  # 'in_stock', 'out_of_stock', 'low_stock'
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # 관계
    product = relationship("AmazonProduct", back_populates="rankings")
    category = relationship("AmazonCategory", back_populates="rankings")

    # 복합 인덱스 (성능 최적화)
    __table_args__ = (
        Index('ix_product_category_time', 'product_id', 'category_id', 'collected_at'),
        Index('ix_category_rank_time', 'category_id', 'rank', 'collected_at'),
    )

    def __repr__(self):
        return f"<AmazonRanking(product_id={self.product_id}, category_id={self.category_id}, rank={self.rank})>"

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "category_id": self.category_id,
            "rank": self.rank,
            "price": float(self.price) if self.price else None,
            "rating": float(self.rating) if self.rating else None,
            "review_count": self.review_count,
            "is_prime": self.is_prime,
            "stock_status": self.stock_status,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None
        }


class ScheduleLog(Base):
    """스케줄 실행 로그 테이블"""
    __tablename__ = "schedule_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(100), nullable=False, index=True)
    job_type = Column(String(50), nullable=True)  # 'amazon_scrape', 'social_scrape', 'insight_generation'
    status = Column(String(20), nullable=False, index=True)  # 'success', 'failed', 'partial'
    items_collected = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time_seconds = Column(Numeric(10, 2), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 인덱스
    __table_args__ = (
        Index('ix_job_time', 'job_name', 'started_at'),
    )

    def __repr__(self):
        return f"<ScheduleLog(job='{self.job_name}', status='{self.status}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "job_name": self.job_name,
            "job_type": self.job_type,
            "status": self.status,
            "items_collected": self.items_collected,
            "error_message": self.error_message,
            "execution_time_seconds": float(self.execution_time_seconds) if self.execution_time_seconds else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
