"""
데이터베이스 연결 및 세션 관리
SQLAlchemy를 사용한 ORM 설정
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from config import settings
from .logging import get_logger

logger = get_logger(__name__)

# Base 클래스 생성 (모든 모델이 상속)
Base = declarative_base()

# 엔진 생성
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,  # 연결 유효성 체크
    pool_recycle=3600,  # 1시간마다 연결 재생성
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_db():
    """
    데이터베이스 초기화
    모든 테이블 생성
    """
    try:
        # 모든 모델 import (테이블 생성을 위해)
        from src.models import amazon, brands, scenario

        logger.info("데이터베이스 테이블 생성 시작...")
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 테이블 생성 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션 제공 (dependency injection용)

    Yields:
        Session: SQLAlchemy 세션

    Example:
        ```python
        from src.core.database import get_db

        with next(get_db()) as db:
            products = db.query(Product).all()
        ```
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"데이터베이스 트랜잭션 에러: {e}")
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    컨텍스트 매니저로 데이터베이스 세션 제공

    Example:
        ```python
        from src.core.database import get_db_context

        with get_db_context() as db:
            product = db.query(Product).first()
        ```
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"데이터베이스 트랜잭션 에러: {e}")
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    데이터베이스 세션 직접 반환 (수동 관리)

    Returns:
        Session: SQLAlchemy 세션

    Note:
        반드시 사용 후 session.close()를 호출해야 합니다.

    Example:
        ```python
        from src.core.database import get_db_session

        db = get_db_session()
        try:
            products = db.query(Product).all()
            db.commit()
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
        ```
    """
    return SessionLocal()


def check_db_connection() -> bool:
    """
    데이터베이스 연결 확인

    Returns:
        bool: 연결 성공 여부
    """
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1"))
        logger.info("데이터베이스 연결 확인 성공")
        return True
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")
        return False
