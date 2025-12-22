#!/usr/bin/env python3
"""
이벤트 감지 테스트 스크립트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from src.core.database import get_db_context
from src.analyzers.event_detector import EventDetector
from config.settings import settings
from loguru import logger


def test_event_detection():
    """이벤트 감지 테스트"""

    logger.info("=" * 80)
    logger.info("이벤트 감지 테스트 시작")
    logger.info("=" * 80)

    detector = EventDetector(
        rank_change_threshold=settings.EVENT_RANK_CHANGE_THRESHOLD,
        rank_change_pct_threshold=settings.EVENT_RANK_CHANGE_PCT_THRESHOLD,
        price_change_pct_threshold=settings.EVENT_PRICE_CHANGE_PCT_THRESHOLD,
        review_surge_threshold=settings.EVENT_REVIEW_SURGE_THRESHOLD
    )

    with get_db_context() as db:
        # 24시간 lookback으로 테스트
        events = detector.detect_events(db, lookback_hours=24)

        logger.info(f"\n{'='*80}")
        logger.info(f"총 {len(events)}개 이벤트 감지")
        logger.info(f"{'='*80}\n")

        if not events:
            logger.warning("감지된 이벤트가 없습니다.")
            logger.info("이벤트를 감지하려면 Amazon 랭킹 데이터가 2회 이상 수집되어 있어야 합니다.")
            return

        # 심각도별 분류
        by_severity = {}
        for event in events:
            severity = event.severity
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(event)

        logger.info("심각도별 분류:")
        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in by_severity:
                count = len(by_severity[severity])
                emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[severity]
                logger.info(f"  {emoji} {severity.upper()}: {count}개")

        logger.info(f"\n{'='*80}")
        logger.info("이벤트 상세:")
        logger.info(f"{'='*80}\n")

        for i, event in enumerate(events, 1):
            logger.info(f"[이벤트 {i}]")
            logger.info(f"  타입: {event.event_type}")
            logger.info(f"  심각도: {event.severity}")
            logger.info(f"  제품 ID: {event.product_id}")

            if event.rank_change:
                logger.info(f"  랭킹 변동: {event.prev_rank}위 → {event.curr_rank}위 ({event.rank_change:+d})")
                logger.info(f"  변동률: {event.rank_change_pct:.1f}%")

            if event.price_change_pct:
                logger.info(f"  가격 변동: ${event.prev_price} → ${event.curr_price} ({event.price_change_pct:+.1f}%)")

            if event.review_change:
                logger.info(f"  리뷰 변동: {event.prev_review_count} → {event.curr_review_count} (+{event.review_change})")

            logger.info(f"  감지 시간: {event.detected_at}")
            logger.info(f"  데이터 수집 범위: {event.time_window_start} ~ {event.time_window_end}")
            logger.info("-" * 80)

        logger.info(f"\n{'='*80}")
        logger.info("테스트 완료")
        logger.info(f"{'='*80}")


if __name__ == "__main__":
    test_event_detection()
