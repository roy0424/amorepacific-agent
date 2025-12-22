"""
랭킹 모니터링 Flow - 6시간마다 실행
Amazon 랭킹을 수집하고 이벤트를 감지합니다.
"""
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact, create_table_artifact
from datetime import timedelta
from loguru import logger

from src.core.database import get_db_context
from src.analyzers.event_detector import EventDetector
from src.tasks.scraping_tasks import scrape_all_amazon_categories_task
from src.tasks.processing_tasks import save_amazon_rankings_task
from src.flows.context_collection_flow import context_collection_flow
from src.flows.insight_generation_flow import insight_generation_flow
from config.settings import settings


@task(name="detect_ranking_events")
def detect_ranking_events_task():
    """랭킹 이벤트 감지"""

    detector = EventDetector(
        rank_change_threshold=settings.EVENT_RANK_CHANGE_THRESHOLD,
        rank_change_pct_threshold=settings.EVENT_RANK_CHANGE_PCT_THRESHOLD,
        price_change_pct_threshold=settings.EVENT_PRICE_CHANGE_PCT_THRESHOLD,
        review_surge_threshold=settings.EVENT_REVIEW_SURGE_THRESHOLD
    )

    with get_db_context() as db:
        events = detector.detect_events(db, lookback_hours=12)

        # 이벤트 DB에 저장
        for event in events:
            db.add(event)

        db.commit()

        logger.info(f"총 {len(events)}개 이벤트 저장 완료")

        return events


@task(name="create_event_summary_artifact")
async def create_event_summary_artifact_task(events):
    """이벤트 요약 Artifact 생성"""

    if not events:
        await create_markdown_artifact(
            key="ranking-events-summary",
            markdown="## 랭킹 이벤트\n\n이번 주기에는 감지된 이벤트가 없습니다.",
            description="랭킹 변동 이벤트 요약"
        )
        return

    # Markdown 요약 생성
    summary_md = "## 🎯 랭킹 이벤트 감지 결과\n\n"
    summary_md += f"**총 {len(events)}개 이벤트 감지**\n\n"

    # 심각도별 분류
    by_severity = {}
    for event in events:
        severity = event.severity
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(event)

    for severity in ['critical', 'high', 'medium', 'low']:
        if severity in by_severity:
            count = len(by_severity[severity])
            emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[severity]
            summary_md += f"- {emoji} **{severity.upper()}**: {count}개\n"

    summary_md += "\n### 상세 내역\n\n"

    for event in events[:10]:  # 최대 10개만 표시
        summary_md += f"#### {event.event_type}\n"
        summary_md += f"- **제품 ID**: {event.product_id}\n"
        summary_md += f"- **심각도**: {event.severity}\n"

        if event.rank_change:
            summary_md += f"- **랭킹 변동**: {event.prev_rank}위 → {event.curr_rank}위 ({event.rank_change:+d})\n"

        if event.price_change_pct:
            summary_md += f"- **가격 변동**: {event.price_change_pct:+.1f}%\n"

        summary_md += f"- **감지 시간**: {event.detected_at}\n\n"

    await create_markdown_artifact(
        key="ranking-events-summary",
        markdown=summary_md,
        description=f"랭킹 변동 이벤트 요약 ({len(events)}개)"
    )

    # 테이블 Artifact
    table_data = []
    for event in events:
        table_data.append({
            "Event Type": event.event_type,
            "Severity": event.severity,
            "Product ID": event.product_id,
            "Rank Change": f"{event.prev_rank}→{event.curr_rank}" if event.rank_change else "-",
            "Detected At": event.detected_at.strftime('%Y-%m-%d %H:%M')
        })

    await create_table_artifact(
        key="ranking-events-table",
        table=table_data,
        description="이벤트 목록"
    )


@flow(
    name="ranking_monitor",
    description="Amazon 랭킹 모니터링 및 이벤트 감지"
)
async def ranking_monitor_flow():
    """
    메인 랭킹 모니터링 Flow

    1. Amazon 랭킹 수집
    2. 이벤트 감지
    3. Critical/High 이벤트 발견 시 Context Collection Flow 트리거
    4. Context 수집 완료 후 Insight Generation Flow 트리거
    """

    logger.info("=" * 80)
    logger.info("Ranking Monitor Flow 시작")
    logger.info("=" * 80)

    # 1. Amazon 랭킹 수집
    logger.info("Step 1: Amazon 랭킹 수집")
    ranking_results = await scrape_all_amazon_categories_task()

    # 2. DB 저장
    logger.info("Step 2: 랭킹 데이터 DB 저장")
    await save_amazon_rankings_task(ranking_results)

    # 3. 이벤트 감지
    logger.info("Step 3: 이벤트 감지")
    events = await detect_ranking_events_task()

    # 4. Artifact 생성
    logger.info("Step 4: Artifact 생성")
    await create_event_summary_artifact_task(events)

    # 5. 이벤트 발견 시 Context Collection Flow 트리거
    context_flows_triggered = 0
    if events:
        logger.info("Step 5: Context Collection Flow 트리거")
        for event in events:
            # Critical 또는 High 심각도 이벤트만 처리
            if event.severity in ['critical', 'high']:
                logger.info(f"  - Event ID {event.id} ({event.event_type}, {event.severity}) 처리 시작")
                try:
                    context_collection_flow(event.id)
                    context_flows_triggered += 1
                except Exception as e:
                    logger.error(f"  - Event ID {event.id} 처리 실패: {e}")

        logger.info(f"총 {context_flows_triggered}개 Context Collection Flow 실행")

    # 6. 인사이트 생성 Flow 트리거 (Context 수집이 완료된 이벤트 대상)
    insight_result = None
    if context_flows_triggered > 0:
        logger.info("Step 6: Insight Generation Flow 트리거")
        try:
            # Context 수집이 완료된 이벤트들에 대해 인사이트 생성
            insight_result = await insight_generation_flow(limit=10)
            logger.info(f"  - 인사이트 생성: {insight_result.get('successful', 0)}개 성공")
        except Exception as e:
            logger.error(f"  - Insight Generation Flow 실패: {e}")

    logger.info("=" * 80)
    logger.info(f"Ranking Monitor Flow 완료 - {len(events)}개 이벤트 감지")
    logger.info(f"  - Context 수집: {context_flows_triggered}개")
    if insight_result:
        logger.info(f"  - 인사이트 생성: {insight_result.get('successful', 0)}개")
    logger.info("=" * 80)

    return {
        'total_categories': len(ranking_results) if ranking_results else 0,
        'events_detected': len(events),
        'context_flows_triggered': context_flows_triggered,
        'insights_generated': insight_result.get('successful', 0) if insight_result else 0,
        'events': [e.to_dict() for e in events]
    }


# Prefect Deployment
if __name__ == "__main__":
    from prefect import serve

    # 6시간마다 실행
    ranking_monitor_deployment = ranking_monitor_flow.to_deployment(
        name="ranking-monitor-6h",
        interval=timedelta(hours=6),
        tags=["amazon", "ranking", "event-detection"]
    )

    serve(ranking_monitor_deployment)
