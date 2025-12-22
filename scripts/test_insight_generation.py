#!/usr/bin/env python3
"""
인사이트 생성 시스템 테스트

Phase 3 구현 검증:
1. ChromaDB 연결
2. Claude API 연결
3. 인사이트 생성 로직
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.insights.vector_store import EventVectorStore
from src.insights.llm_client import ClaudeClient
from src.insights.event_insight_generator import EventInsightGenerator
from src.core.database import get_db_context
from sqlalchemy import select
from src.models.events import RankingEvent


def test_chromadb():
    """ChromaDB 연결 테스트"""
    logger.info("=" * 60)
    logger.info("1. ChromaDB 연결 테스트")
    logger.info("=" * 60)

    try:
        vector_store = EventVectorStore()
        count = vector_store.get_event_count()
        logger.info(f"✅ ChromaDB 연결 성공 - 저장된 이벤트: {count}개")
        return True
    except Exception as e:
        logger.error(f"❌ ChromaDB 연결 실패: {e}")
        return False


def test_claude_api():
    """Claude API 연결 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("2. Claude API 연결 테스트")
    logger.info("=" * 60)

    try:
        client = ClaudeClient()
        success = client.test_connection()
        if success:
            logger.info("✅ Claude API 연결 성공")
        else:
            logger.error("❌ Claude API 연결 실패")
        return success
    except Exception as e:
        logger.error(f"❌ Claude API 연결 실패: {e}")
        logger.error("ANTHROPIC_API_KEY 환경 변수를 확인하세요")
        return False


def test_vector_embedding():
    """벡터 임베딩 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("3. 벡터 임베딩 테스트")
    logger.info("=" * 60)

    try:
        vector_store = EventVectorStore()

        # 테스트 이벤트 데이터
        test_event = {
            'event_type': 'RANK_SURGE',
            'severity': 'high',
            'rank_change': -15,
            'rank_change_pct': 45.0,
            'product_name': 'Test Product',
            'category_name': 'Beauty'
        }

        # 임베딩 추가
        vector_store.add_event(
            event_id=99999,
            event_data=test_event
        )

        # 유사 이벤트 검색
        similar = vector_store.search_similar_events(test_event, top_k=3)

        logger.info(f"✅ 벡터 임베딩 성공 - 유사 이벤트 {len(similar)}개 발견")

        # 테스트 데이터 삭제 (옵션)
        # vector_store.collection.delete(ids=["event_99999"])

        return True
    except Exception as e:
        logger.error(f"❌ 벡터 임베딩 실패: {e}")
        return False


def test_insight_generation():
    """인사이트 생성 테스트 (실제 이벤트가 있는 경우)"""
    logger.info("\n" + "=" * 60)
    logger.info("4. 인사이트 생성 테스트")
    logger.info("=" * 60)

    try:
        # DB에서 이벤트 찾기
        with get_db_context() as db:
            event = db.execute(
                select(RankingEvent).where(
                    RankingEvent.context_collected == True,
                    RankingEvent.insight_generated == False
                ).limit(1)
            ).scalar_one_or_none()

            if not event:
                logger.warning("⚠️  인사이트 생성 가능한 이벤트가 없습니다")
                logger.info("   (Context 수집이 완료되었지만 인사이트가 생성되지 않은 이벤트)")
                logger.info("   실제 이벤트가 발생한 후 다시 테스트하세요")
                return None

            logger.info(f"테스트 이벤트 발견: ID {event.id} ({event.event_type}, {event.severity})")

            # 인사이트 생성
            generator = EventInsightGenerator()
            insight = generator.generate_insight(db, event.id)

            if insight:
                logger.info("✅ 인사이트 생성 성공")
                logger.info(f"   - 인사이트 ID: {insight.id}")
                logger.info(f"   - 요약: {insight.summary[:100]}...")
                logger.info(f"   - 신뢰도: {insight.confidence_score:.2f}")
                logger.info(f"   - 모델: {insight.llm_model}")
                return True
            else:
                logger.error("❌ 인사이트 생성 실패")
                return False

    except Exception as e:
        logger.error(f"❌ 인사이트 생성 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 실행"""
    logger.info("\n" + "=" * 60)
    logger.info("Phase 3: RAG + LLM 인사이트 생성 시스템 테스트")
    logger.info("=" * 60)

    results = {}

    # 1. ChromaDB 테스트
    results['chromadb'] = test_chromadb()

    # 2. Claude API 테스트
    results['claude_api'] = test_claude_api()

    # 3. 벡터 임베딩 테스트
    if results['chromadb']:
        results['vector_embedding'] = test_vector_embedding()
    else:
        results['vector_embedding'] = False

    # 4. 인사이트 생성 테스트 (실제 이벤트가 있는 경우만)
    if results['claude_api'] and results['chromadb']:
        result = test_insight_generation()
        results['insight_generation'] = result if result is not None else 'skipped'
    else:
        results['insight_generation'] = False

    # 최종 결과
    logger.info("\n" + "=" * 60)
    logger.info("테스트 결과 요약")
    logger.info("=" * 60)

    for test_name, result in results.items():
        if result is True:
            status = "✅ 성공"
        elif result == 'skipped':
            status = "⚠️  스킵됨"
        else:
            status = "❌ 실패"
        logger.info(f"{test_name:20s}: {status}")

    # 성공한 테스트 개수
    success_count = sum(1 for r in results.values() if r is True)
    total_count = len([r for r in results.values() if r != 'skipped'])

    logger.info("=" * 60)
    logger.info(f"전체: {success_count}/{total_count} 테스트 성공")
    logger.info("=" * 60)

    if success_count == total_count:
        logger.info("\n🎉 모든 테스트가 성공했습니다!")
        logger.info("Phase 3 구현이 완료되었습니다.")
    else:
        logger.warning("\n⚠️  일부 테스트가 실패했습니다.")
        logger.info("실패한 테스트를 확인하고 수정하세요.")


if __name__ == "__main__":
    main()
