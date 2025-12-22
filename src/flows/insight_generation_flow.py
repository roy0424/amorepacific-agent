"""
Insight Generation Flow - 인사이트 생성 Flow
Context 수집이 완료된 이벤트에 대해 LLM 인사이트 생성
"""
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from loguru import logger
from sqlalchemy import select, and_
from typing import List

from src.core.database import get_db_context
from src.models.events import RankingEvent, EventInsight
from src.insights.event_insight_generator import EventInsightGenerator


@task(name="find_events_ready_for_insight")
def find_events_ready_for_insight_task(limit: int = 10) -> List[int]:
    """
    인사이트 생성 준비가 된 이벤트 찾기

    컨텍스트 수집은 완료되었지만 인사이트가 아직 생성되지 않은
    critical/high 심각도 이벤트를 선택

    Args:
        limit: 최대 이벤트 개수

    Returns:
        이벤트 ID 목록
    """
    with get_db_context() as db:
        events = db.execute(
            select(RankingEvent).where(
                and_(
                    RankingEvent.context_collected == True,
                    RankingEvent.insight_generated == False,
                    RankingEvent.severity.in_(['critical', 'high'])
                )
            ).limit(limit)
        ).scalars().all()

        event_ids = [e.id for e in events]

        logger.info(f"인사이트 생성 대기 중인 이벤트: {len(event_ids)}개")
        return event_ids


@task(name="generate_event_insight")
def generate_event_insight_task(event_id: int) -> dict:
    """
    단일 이벤트에 대한 인사이트 생성

    Args:
        event_id: 이벤트 ID

    Returns:
        인사이트 정보
    """
    logger.info(f"이벤트 {event_id} 인사이트 생성 시작")

    generator = EventInsightGenerator()

    with get_db_context() as db:
        try:
            insight = generator.generate_insight(db, event_id)

            if insight:
                return {
                    'event_id': event_id,
                    'success': True,
                    'insight_id': insight.id,
                    'summary': insight.summary,
                    'confidence_score': insight.confidence_score
                }
            else:
                return {
                    'event_id': event_id,
                    'success': False,
                    'error': 'Failed to generate insight'
                }

        except Exception as e:
            logger.error(f"이벤트 {event_id} 인사이트 생성 실패: {e}")
            return {
                'event_id': event_id,
                'success': False,
                'error': str(e)
            }


@task(name="create_insight_summary_artifact")
async def create_insight_summary_artifact_task(insights: List[dict]):
    """
    생성된 인사이트 요약 Artifact 생성

    Args:
        insights: 인사이트 정보 목록
    """
    if not insights:
        await create_markdown_artifact(
            key="insights-summary",
            markdown="## 인사이트 생성\\n\\n이번 주기에는 생성된 인사이트가 없습니다.",
            description="인사이트 생성 요약"
        )
        return

    # 성공/실패 집계
    successful = [i for i in insights if i.get('success')]
    failed = [i for i in insights if not i.get('success')]

    # Markdown 요약 생성
    summary_md = "## 🧠 인사이트 생성 결과\\n\\n"
    summary_md += f"**총 {len(insights)}개 이벤트 처리**\\n"
    summary_md += f"- ✅ 성공: {len(successful)}개\\n"
    summary_md += f"- ❌ 실패: {len(failed)}개\\n\\n"

    # 성공한 인사이트 목록
    if successful:
        summary_md += "### 생성된 인사이트\\n\\n"
        for i, insight in enumerate(successful[:10], 1):
            summary_md += f"#### {i}. 이벤트 #{insight['event_id']}\\n"
            summary_md += f"- **요약**: {insight.get('summary', 'N/A')}\\n"
            summary_md += f"- **신뢰도**: {insight.get('confidence_score', 0):.2f}\\n"
            summary_md += f"- **인사이트 ID**: {insight.get('insight_id')}\\n\\n"

    # 실패한 이벤트
    if failed:
        summary_md += "### 실패한 이벤트\\n\\n"
        for i, insight in enumerate(failed, 1):
            summary_md += f"{i}. 이벤트 #{insight['event_id']}: {insight.get('error', 'Unknown error')}\\n"

    await create_markdown_artifact(
        key="insights-summary",
        markdown=summary_md,
        description=f"인사이트 생성 요약 ({len(successful)}개 성공)"
    )


@flow(
    name="insight_generation",
    description="이벤트 인사이트 생성 (RAG + LLM)"
)
async def insight_generation_flow(event_ids: List[int] = None, limit: int = 10):
    """
    인사이트 생성 Flow

    1. 인사이트 생성 대기 중인 이벤트 찾기
    2. 각 이벤트에 대해 RAG + LLM 인사이트 생성
    3. 결과 요약 Artifact 생성

    Args:
        event_ids: 처리할 이벤트 ID 목록 (None이면 자동 선택)
        limit: 자동 선택 시 최대 이벤트 개수
    """
    logger.info("=" * 80)
    logger.info("Insight Generation Flow 시작")
    logger.info("=" * 80)

    # 1. 이벤트 선택
    if event_ids is None:
        logger.info("Step 1: 인사이트 생성 대기 이벤트 찾기")
        event_ids = await find_events_ready_for_insight_task(limit=limit)
    else:
        logger.info(f"Step 1: 지정된 이벤트 처리 ({len(event_ids)}개)")

    if not event_ids:
        logger.info("처리할 이벤트가 없습니다")
        await create_insight_summary_artifact_task([])
        return {
            'processed': 0,
            'successful': 0,
            'failed': 0
        }

    # 2. 각 이벤트에 대해 인사이트 생성
    logger.info(f"Step 2: {len(event_ids)}개 이벤트 인사이트 생성")
    insights = []
    for event_id in event_ids:
        try:
            insight_result = await generate_event_insight_task(event_id)
            insights.append(insight_result)
        except Exception as e:
            logger.error(f"이벤트 {event_id} 처리 중 오류: {e}")
            insights.append({
                'event_id': event_id,
                'success': False,
                'error': str(e)
            })

    # 3. 결과 요약 Artifact 생성
    logger.info("Step 3: 인사이트 요약 Artifact 생성")
    await create_insight_summary_artifact_task(insights)

    # 4. 결과 집계
    successful = [i for i in insights if i.get('success')]
    failed = [i for i in insights if not i.get('success')]

    logger.info("=" * 80)
    logger.info(f"Insight Generation Flow 완료")
    logger.info(f"  - 처리: {len(insights)}개")
    logger.info(f"  - 성공: {len(successful)}개")
    logger.info(f"  - 실패: {len(failed)}개")
    logger.info("=" * 80)

    return {
        'processed': len(insights),
        'successful': len(successful),
        'failed': len(failed),
        'insights': insights
    }


if __name__ == "__main__":
    import asyncio

    # 테스트: 인사이트 생성 Flow 실행
    asyncio.run(insight_generation_flow())
