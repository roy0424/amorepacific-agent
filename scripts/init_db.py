"""
데이터베이스 초기화 스크립트
테이블 생성 및 초기 데이터 시딩
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.database import init_db, get_db_context, check_db_connection
from src.core.logging import setup_logging, get_logger
from src.models import (
    Brand, AmazonCategory,
    YouTubeVideo, YouTubeMetric,
    TikTokPost, TikTokMetric,
    InstagramPost, InstagramMetric,
    ScenarioCategory, ScenarioProduct
)
from config import settings
import json

setup_logging()
logger = get_logger(__name__)


def seed_brands():
    """브랜드 초기 데이터 시딩"""
    logger.info("브랜드 데이터 시딩 시작...")

    brands_data = [
        {
            "name": "Laneige",
            "brand_type": "target",
            "keywords": json.dumps(["laneige", "라네즈", "laneige lip sleeping mask"]),
            "is_active": True
        },
        {
            "name": "Vaseline",
            "brand_type": "competitor",
            "keywords": json.dumps(["vaseline", "vaseline lip therapy"]),
            "is_active": True
        },
        {
            "name": "CeraVe",
            "brand_type": "competitor",
            "keywords": json.dumps(["cerave", "cerave moisturizing cream"]),
            "is_active": True
        },
        {
            "name": "Neutrogena",
            "brand_type": "competitor",
            "keywords": json.dumps(["neutrogena", "neutrogena hydro boost"]),
            "is_active": True
        },
        {
            "name": "e.l.f.",
            "brand_type": "competitor",
            "keywords": json.dumps(["elf cosmetics", "elf makeup"]),
            "is_active": True
        }
    ]

    with get_db_context() as db:
        for brand_data in brands_data:
            # 이미 존재하는지 확인
            existing = db.query(Brand).filter(Brand.name == brand_data["name"]).first()
            if existing:
                logger.info(f"브랜드 '{brand_data['name']}'는 이미 존재합니다. 스킵.")
                continue

            brand = Brand(**brand_data)
            db.add(brand)
            logger.info(f"브랜드 추가: {brand_data['name']} ({brand_data['brand_type']})")

        db.commit()
        logger.info(f"브랜드 데이터 시딩 완료: {len(brands_data)}개")


def seed_categories():
    """아마존 카테고리 초기 데이터 시딩"""
    logger.info("아마존 카테고리 데이터 시딩 시작...")

    categories_data = [
        {
            "category_name": "Beauty & Personal Care",
            "category_url": "https://www.amazon.com/Best-Sellers-Beauty/zgbs/beauty",
            "parent_category_id": None
        },
        {
            "category_name": "Lip Care",
            "category_url": "https://www.amazon.com/Best-Sellers-Lip-Care/zgbs/beauty/3761351",
            "parent_category_id": None  # 나중에 업데이트
        },
        {
            "category_name": "Skin Care",
            "category_url": "https://www.amazon.com/Best-Sellers-Skin-Care/zgbs/beauty/11060451",
            "parent_category_id": None
        },
        {
            "category_name": "Lip Makeup",
            "category_url": "https://www.amazon.com/Best-Sellers-Lip-Makeup/zgbs/beauty/11059031",
            "parent_category_id": None
        },
        {
            "category_name": "Face Powder",
            "category_url": "https://www.amazon.com/Best-Sellers-Face-Powder/zgbs/beauty/11058971",
            "parent_category_id": None
        }
    ]

    with get_db_context() as db:
        for category_data in categories_data:
            # 이미 존재하는지 확인
            existing = db.query(AmazonCategory).filter(
                AmazonCategory.category_name == category_data["category_name"]
            ).first()
            if existing:
                logger.info(f"카테고리 '{category_data['category_name']}'는 이미 존재합니다. 스킵.")
                continue

            category = AmazonCategory(**category_data)
            db.add(category)
            logger.info(f"카테고리 추가: {category_data['category_name']}")

        db.commit()
        logger.info(f"카테고리 데이터 시딩 완료: {len(categories_data)}개")


def seed_scenario_data():
    """시나리오 테스트용 기본 더미 데이터 시딩"""
    logger.info("시나리오 더미 데이터 시딩 시작...")

    scenario_categories = [
        "Lip Care",
        "Skin Care",
        "Moisturizers",
        "Face Masks",
        "Cleansers",
    ]
    scenario_products = [
        {"name": "Laneige Lip Sleeping Mask", "asin": "B0009V1Z0S"},
        {"name": "Laneige Water Sleeping Mask", "asin": "B00R9D5J3O"},
        {"name": "Laneige Cream Skin Toner & Moisturizer", "asin": "B07Q7NWXK3"},
        {"name": "Laneige Water Bank Blue Hyaluronic Cream", "asin": "B0B9F3BSW5"},
        {"name": "Laneige Water Bank Blue Hyaluronic Serum", "asin": "B0B9F3S1P7"},
        {"name": "Laneige Lip Glowy Balm", "asin": "B07ZHB7G5Q"},
        {"name": "Laneige Bouncy & Firm Sleeping Mask", "asin": "B0C9BG1C7Q"},
        {"name": "Laneige Water Bank Cleansing Foam", "asin": "B0B9F6Z2RQ"},
        {"name": "Laneige Cream Skin Refiner", "asin": "B07Q7P5F7S"},
        {"name": "Laneige Water Bank Blue Hyaluronic Eye Cream", "asin": "B0B9F5ZJ1M"},
    ]

    with get_db_context() as db:
        for name in scenario_categories:
            existing = db.query(ScenarioCategory).filter(
                ScenarioCategory.category_name == name
            ).first()
            if existing:
                continue
            db.add(ScenarioCategory(category_name=name))

        for product in scenario_products:
            existing = db.query(ScenarioProduct).filter(
                ScenarioProduct.product_name == product["name"]
            ).first()
            if existing:
                continue
            db.add(ScenarioProduct(
                asin=product["asin"],
                product_name=product["name"],
                brand_id=1
            ))

        db.commit()
        logger.info("시나리오 더미 데이터 시딩 완료")


def main():
    """메인 실행 함수"""
    try:
        logger.info("=" * 60)
        logger.info("데이터베이스 초기화 시작")
        logger.info("=" * 60)

        # 데이터베이스 연결 확인
        if not check_db_connection():
            logger.error("데이터베이스 연결 실패. 환경 변수를 확인하세요.")
            sys.exit(1)

        # 테이블 생성
        logger.info(f"데이터베이스 URL: {settings.DATABASE_URL}")
        init_db()

        # 초기 데이터 시딩
        seed_brands()
        seed_categories()
        seed_scenario_data()

        logger.info("=" * 60)
        logger.info("데이터베이스 초기화 완료!")
        logger.info("=" * 60)

        # 결과 확인
        with get_db_context() as db:
            brand_count = db.query(Brand).count()
            category_count = db.query(AmazonCategory).count()

            logger.info(f"총 브랜드 수: {brand_count}")
            logger.info(f"총 카테고리 수: {category_count}")

    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
