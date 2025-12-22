"""
로깅 설정
Loguru를 사용한 구조화된 로깅
"""
import sys
from loguru import logger
from pathlib import Path
from config import settings


def setup_logging():
    """로깅 설정 초기화"""

    # 기본 핸들러 제거
    logger.remove()

    # 콘솔 로그 (stdout)
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # 일반 애플리케이션 로그 (일별 로테이션)
    logger.add(
        settings.LOGS_DIR / "app_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=settings.LOG_ROTATION,
        retention=f"{settings.LOG_RETENTION_DAYS} days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )

    # 에러 로그 (별도 파일)
    logger.add(
        settings.LOGS_DIR / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
        rotation=settings.LOG_ROTATION,
        retention=f"{settings.LOG_RETENTION_DAYS * 3} days",  # 에러는 3배 길게 보관
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )

    # 크롤링 로그 (별도 파일)
    logger.add(
        settings.LOGS_DIR / "scraping_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        rotation=settings.LOG_ROTATION,
        retention=f"{settings.LOG_RETENTION_DAYS} days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: "scraper" in record["name"].lower()
    )

    logger.info("로깅 시스템 초기화 완료")
    logger.info(f"로그 디렉토리: {settings.LOGS_DIR}")
    logger.info(f"로그 레벨: {settings.LOG_LEVEL}")


def get_logger(name: str):
    """
    모듈별 로거 반환

    Args:
        name: 모듈 이름 (보통 __name__)

    Returns:
        logger: 설정된 로거 인스턴스
    """
    return logger.bind(name=name)


# 애플리케이션 시작 시 로깅 설정
if __name__ != "__main__":
    setup_logging()
