"""
브랜드 모델
타겟 브랜드(라네즈) 및 경쟁사 브랜드 정보
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ARRAY, Text
from sqlalchemy.sql import func
from src.core.database import Base


class Brand(Base):
    """브랜드 테이블"""
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    brand_type = Column(String(20), nullable=False, index=True)  # 'target' or 'competitor'
    keywords = Column(Text, nullable=True)  # JSON string으로 저장
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Brand(name='{self.name}', type='{self.brand_type}')>"

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "brand_type": self.brand_type,
            "keywords": self.keywords,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
