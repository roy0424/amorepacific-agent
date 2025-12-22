"""
Context Collection Flow - 이벤트 발생 시 원인 데이터 수집
이벤트 전후 시간 범위 내의 소셜미디어 데이터를 수집합니다.
"""
from prefect import flow, task
from datetime import datetime
from loguru import logger
from sqlalchemy import select, and_

from src.core.database import get_db_context
from src.models.events import RankingEvent, EventContextSocial
from src.models.social_media import YouTubeVideo, YouTubeMetric, TikTokPost, TikTokMetric, InstagramPost, InstagramMetric


@task(name="load_event_info")
def load_event_info_task(event_id: int):
    """이벤트 정보 로드"""

    with get_db_context() as db:
        event = db.execute(
            select(RankingEvent).where(RankingEvent.id == event_id)
        ).scalar_one_or_none()

        if not event:
            raise ValueError(f"Event ID {event_id} not found")

        logger.info(f"이벤트 정보 로드: {event.event_type} (심각도: {event.severity})")
        logger.info(f"데이터 수집 범위: {event.time_window_start} ~ {event.time_window_end}")

        return {
            'event_id': event.id,
            'product_id': event.product_id,
            'event_type': event.event_type,
            'severity': event.severity,
            'time_window_start': event.time_window_start,
            'time_window_end': event.time_window_end
        }


@task(name="collect_social_media_context")
def collect_social_media_context_task(event_info: dict):
    """
    시간 범위 내 소셜미디어 데이터 수집

    기존에 수집된 소셜미디어 데이터 중
    이벤트 시간 범위에 해당하는 것들을 찾아서
    event_context_social 테이블에 저장
    """

    event_id = event_info['event_id']
    time_start = event_info['time_window_start']
    time_end = event_info['time_window_end']

    logger.info(f"소셜미디어 컨텍스트 수집 중... ({time_start} ~ {time_end})")

    social_context_count = 0

    with get_db_context() as db:
        # 1. YouTube 데이터
        youtube_query = select(YouTubeVideo, YouTubeMetric).join(
            YouTubeMetric,
            YouTubeVideo.id == YouTubeMetric.video_id
        ).where(
            and_(
                YouTubeVideo.published_at >= time_start,
                YouTubeVideo.published_at <= time_end
            )
        ).order_by(YouTubeMetric.view_count.desc()).limit(30)

        youtube_results = db.execute(youtube_query).all()

        for video, metric in youtube_results:
            engagement_score = (
                (metric.like_count or 0) +
                (metric.comment_count or 0) * 2
            )

            # 바이럴 여부 판단 (view count 기준)
            is_viral = metric.view_count and metric.view_count > 100000

            context = EventContextSocial(
                event_id=event_id,
                platform='youtube',
                content_id=video.video_id,
                author=video.channel_title or '',
                text=f"{video.title or ''} {video.description or ''}",
                hashtags=video.tags or '',
                view_count=metric.view_count,
                like_count=metric.like_count,
                comment_count=metric.comment_count,
                share_count=0,
                engagement_score=engagement_score,
                posted_at=video.published_at,
                is_viral=is_viral
            )
            db.add(context)
            social_context_count += 1

        # 2. TikTok 데이터
        tiktok_query = select(TikTokPost, TikTokMetric).join(
            TikTokMetric,
            TikTokPost.id == TikTokMetric.post_id
        ).where(
            and_(
                TikTokPost.posted_at >= time_start,
                TikTokPost.posted_at <= time_end
            )
        ).order_by(TikTokMetric.view_count.desc()).limit(30)

        tiktok_results = db.execute(tiktok_query).all()

        for post, metric in tiktok_results:
            engagement_score = (
                (metric.like_count or 0) +
                (metric.comment_count or 0) * 2 +
                (metric.share_count or 0) * 3
            )

            is_viral = metric.view_count and metric.view_count > 500000

            context = EventContextSocial(
                event_id=event_id,
                platform='tiktok',
                content_id=post.video_id,
                author=post.author_username or '',
                text=post.description or '',
                hashtags=post.hashtags or '',
                view_count=metric.view_count,
                like_count=metric.like_count,
                comment_count=metric.comment_count,
                share_count=metric.share_count,
                engagement_score=engagement_score,
                posted_at=post.posted_at,
                is_viral=is_viral
            )
            db.add(context)
            social_context_count += 1

        # 3. Instagram 데이터
        instagram_query = select(InstagramPost, InstagramMetric).join(
            InstagramMetric,
            InstagramPost.id == InstagramMetric.post_id
        ).where(
            and_(
                InstagramPost.posted_at >= time_start,
                InstagramPost.posted_at <= time_end
            )
        ).order_by(InstagramMetric.like_count.desc()).limit(30)

        instagram_results = db.execute(instagram_query).all()

        for post, metric in instagram_results:
            engagement_score = (
                (metric.like_count or 0) +
                (metric.comment_count or 0) * 2
            )

            is_viral = metric.like_count and metric.like_count > 50000

            context = EventContextSocial(
                event_id=event_id,
                platform='instagram',
                content_id=post.shortcode,
                author=post.owner_username or '',
                text=post.caption or '',
                hashtags=post.hashtags or '',
                view_count=metric.video_view_count or 0,
                like_count=metric.like_count,
                comment_count=metric.comment_count,
                share_count=0,
                engagement_score=engagement_score,
                posted_at=post.posted_at,
                is_viral=is_viral
            )
            db.add(context)
            social_context_count += 1

        db.commit()

    logger.info(f"소셜미디어 컨텍스트 {social_context_count}개 수집 완료")

    return {
        'social_context_count': social_context_count
    }


@task(name="update_event_status")
def update_event_status_task(event_id: int, context_collected: bool = True):
    """이벤트 처리 상태 업데이트"""

    with get_db_context() as db:
        event = db.execute(
            select(RankingEvent).where(RankingEvent.id == event_id)
        ).scalar_one()

        event.context_collected = context_collected
        db.commit()

    logger.info(f"이벤트 ID {event_id} 상태 업데이트: context_collected={context_collected}")


@flow(
    name="context_collection",
    description="이벤트 원인 데이터 수집"
)
def context_collection_flow(event_id: int):
    """
    이벤트 원인 데이터 수집 Flow

    1. 이벤트 정보 로드
    2. 시간 범위 내 소셜미디어 데이터 수집
    3. (향후) 리뷰 데이터 수집
    4. (향후) 경쟁사 데이터 수집
    5. 이벤트 상태 업데이트
    """

    logger.info("=" * 80)
    logger.info(f"Context Collection Flow 시작 - Event ID: {event_id}")
    logger.info("=" * 80)

    # 1. 이벤트 정보 로드
    event_info = load_event_info_task(event_id)

    # 2. 소셜미디어 데이터 수집
    social_result = collect_social_media_context_task(event_info)

    # 3. TODO: 리뷰 데이터 수집 (Phase 2 확장)
    # review_result = collect_reviews_task(event_info)

    # 4. TODO: 경쟁사 데이터 수집 (Phase 2 확장)
    # competitor_result = collect_competitor_data_task(event_info)

    # 5. 이벤트 상태 업데이트
    update_event_status_task(event_id, context_collected=True)

    logger.info("=" * 80)
    logger.info(f"Context Collection Flow 완료")
    logger.info(f"  - 소셜미디어: {social_result['social_context_count']}개")
    logger.info("=" * 80)

    return {
        'event_id': event_id,
        'social_context_count': social_result['social_context_count'],
        'context_collected': True
    }


if __name__ == "__main__":
    # 테스트: 특정 이벤트 ID로 실행
    import sys
    if len(sys.argv) > 1:
        test_event_id = int(sys.argv[1])
        context_collection_flow(test_event_id)
    else:
        print("Usage: python context_collection_flow.py <event_id>")
