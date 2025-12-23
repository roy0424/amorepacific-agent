"""
중앙 설정 관리
모든 환경 변수와 애플리케이션 설정을 관리합니다.
"""
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Project Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = DATA_DIR / "logs"
    BACKUPS_DIR: Path = DATA_DIR / "backups"
    REPORTS_DIR: Path = DATA_DIR / "reports"

    # Database Configuration
    DATABASE_URL: str = "postgresql+psycopg://laneige:laneige@postgres:5432/laneige_tracker"
    DB_ECHO: bool = False  # SQLAlchemy echo (디버깅용)

    # Anthropic (Claude) Configuration - RAG + Insight 생성용
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_TEMPERATURE: float = 0.3
    ANTHROPIC_MAX_TOKENS: int = 4096

    # OpenAI Configuration (선택)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4.1"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_TOKENS: int = 2000

    # YouTube Configuration
    YOUTUBE_API_KEY: str
    YOUTUBE_MAX_RESULTS: int = 50

    # TikTok Configuration (optional)
    TIKTOK_SESSION_ID: Optional[str] = None

    # Instagram Configuration (optional)
    INSTAGRAM_USERNAME: Optional[str] = None
    INSTAGRAM_PASSWORD: Optional[str] = None

    # Playwright/Scraping Configuration
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT: int = 30000  # milliseconds
    SCRAPING_DELAY_MIN: float = 1.0
    SCRAPING_DELAY_MAX: float = 3.0
    MAX_RETRIES: int = 3

    # Scheduling Configuration
    AMAZON_SCRAPE_INTERVAL_HOURS: int = 1
    SOCIAL_SCRAPE_INTERVAL_HOURS: int = 6
    INSIGHT_GENERATION_HOUR: int = 9  # 매일 오전 9시
    DAILY_REPORT_HOUR: int = 9
    WEEKLY_REPORT_DAY: str = "mon"  # 월요일
    WEEKLY_REPORT_HOUR: int = 10
    PREFECT_WORK_POOL_NAME: str = "default-process"
    PREFECT_WORK_QUEUE_NAME: str = "default"
    PREFECT_DEPLOY_IMAGE: str = "laneige-tracker:latest"
    PREFECT_USE_SERVE: bool = True

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_RETENTION_DAYS: int = 30
    LOG_ROTATION: str = "1 day"
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"

    # Backup Configuration
    ENABLE_JSON_BACKUP: bool = True
    JSON_BACKUP_PATH: str = "data/backups"
    BACKUP_RETENTION_DAYS: int = 90

    # Report Configuration
    REPORT_OUTPUT_PATH: str = "data/reports"
    REPORT_FILENAME_FORMAT: str = "Laneige_Ranking_Report_{date}.xlsx"

    # Monitoring Configuration
    ENABLE_MONITORING: bool = True
    HEALTH_CHECK_INTERVAL_MINUTES: int = 5

    # Proxy Configuration (optional)
    USE_PROXY: bool = False
    PROXY_URL: Optional[str] = None
    PROXY_USERNAME: Optional[str] = None
    PROXY_PASSWORD: Optional[str] = None

    # Amazon Configuration
    AMAZON_BASE_URL: str = "https://www.amazon.com"
    AMAZON_MAX_PRODUCTS_PER_CATEGORY: int = 100  # 베스트셀러 수집 개수 (50 or 100)

    # Amazon Categories
    AMAZON_CATEGORIES: dict = {
        "beauty": {
            "name": "Beauty & Personal Care",
            "url": "https://www.amazon.com/Best-Sellers-Beauty/zgbs/beauty"
        },
        "lip_care": {
            "name": "Lip Care",
            "url": "https://www.amazon.com/Best-Sellers-Lip-Care/zgbs/beauty/3761351"
        },
        "skin_care": {
            "name": "Skin Care",
            "url": "https://www.amazon.com/Best-Sellers-Skin-Care/zgbs/beauty/11060451"
        },
        "lip_makeup": {
            "name": "Lip Makeup",
            "url": "https://www.amazon.com/Best-Sellers-Lip-Makeup/zgbs/beauty/11059031"
        },
        "face_powder": {
            "name": "Face Powder",
            "url": "https://www.amazon.com/Best-Sellers-Face-Powder/zgbs/beauty/11058971"
        }
    }

    # Target Brands
    TARGET_BRANDS: list = ["laneige", "라네즈"]
    COMPETITOR_BRANDS: list = ["vaseline", "cerave", "neutrogena", "elf", "maybelline"]

    # Social Media Keywords
    SOCIAL_MEDIA_KEYWORDS: dict = {
        "tiktok": ["#laneige", "#laniegelipmask", "#laneigesleepingmask"],
        "youtube": ["laneige", "laneige lip sleeping mask", "laneige review"],
        "instagram": ["#laneige", "#laniegekorea", "#laniegelipmask"]
    }

    # Analysis Thresholds
    SIGNIFICANT_RANK_CHANGE_THRESHOLD: int = 10  # 10위 이상 변동 시 유의미
    SURGE_THRESHOLD_PERCENT: float = 50.0  # 50% 이상 상승
    DROP_THRESHOLD_PERCENT: float = 50.0  # 50% 이상 하락
    CORRELATION_STRONG_THRESHOLD: float = 0.7  # 상관계수 0.7 이상

    # Event Detection Thresholds (개선된 방식)
    # 트렌드 분석 설정
    EVENT_TREND_ANALYSIS_HOURS: int = 12  # 트렌드 분석할 시간 범위
    EVENT_TREND_MIN_DATA_POINTS: int = 3  # 최소 필요한 데이터 포인트
    EVENT_TREND_CONSISTENCY_THRESHOLD: float = 0.6  # 트렌드 일관성 (60% 이상)
    EVENT_TREND_WINDOWS_HOURS: list = [1, 6, 24]  # 다중 시간창 분석
    EVENT_SURGE_WINDOW_HOURS: int = 1  # 급등/급락 판단용 시간창
    EVENT_STEADY_WINDOW_HOURS: int = 24  # 지속상승/하락 판단용 시간창
    EVENT_STEADY_CONSISTENCY_MIN: float = 0.8  # 지속상승/하락 최소 일관성

    # 순위 구간별 임계값 (하이브리드 방식)
    EVENT_RANK_THRESHOLDS: dict = {
        'tier1': {'range': (1, 5),    'threshold': 2},   # 초상위권
        'tier2': {'range': (6, 10),   'threshold': 3},   # 상위권
        'tier3': {'range': (11, 20),  'threshold': 5},   # 중상위권
        'tier4': {'range': (21, 30),  'threshold': 7},   # 중위권
        'tier5': {'range': (31, 50),  'threshold': 10},  # 중하위권
        'tier6': {'range': (51, 100), 'threshold': 15},  # 하위권
    }

    # 퍼센트 기반 임계값 (보조)
    EVENT_RANK_CHANGE_PCT_THRESHOLD: float = 30.0  # 순위 변동 임계값 (퍼센트)
    EVENT_USE_HYBRID_THRESHOLD: bool = True  # 둘 중 하나만 충족해도 이벤트

    # 기타 임계값
    EVENT_PRICE_CHANGE_PCT_THRESHOLD: float = 20.0  # 가격 변동 임계값
    EVENT_REVIEW_SURGE_THRESHOLD: int = 100  # 리뷰 급증 임계값

    # Event Time Windows
    EVENT_LOOKBACK_DAYS: int = 7  # 이벤트 전 데이터 수집 기간
    EVENT_LOOKFORWARD_DAYS: int = 3  # 이벤트 후 데이터 수집 기간

    # LLM Cost Optimization
    LLM_CALL_RATE_LIMIT: int = 100  # 시간당 최대 LLM 호출 수
    ENABLE_LLM_CACHE: bool = True
    LLM_CACHE_TTL: int = 3600  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 디렉토리 생성
        self.DATA_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)
        self.BACKUPS_DIR.mkdir(exist_ok=True)
        self.REPORTS_DIR.mkdir(exist_ok=True)

    @property
    def database_url_async(self) -> str:
        """비동기 데이터베이스 URL (asyncpg 사용 시)"""
        if self.DATABASE_URL.startswith("postgresql+psycopg://"):
            return self.DATABASE_URL.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL

    def get_user_agent_list(self) -> list:
        """User-Agent 리스트 반환"""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ]


# 싱글톤 인스턴스 생성
settings = Settings()
