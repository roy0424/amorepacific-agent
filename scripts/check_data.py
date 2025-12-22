#!/usr/bin/env python3
"""
데이터 수집 현황 확인 스크립트

수집된 데이터의 현황을 한눈에 확인할 수 있습니다.
- Amazon 랭킹 데이터
- 이벤트 발생 현황
- 소셜 미디어 데이터
- Context 수집 현황
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta

from src.core.database import get_db_context
from src.models import (
    AmazonProduct, AmazonRanking, AmazonCategory,
    RankingEvent, EventContextSocial, EventInsight,
    YouTubeVideo, TikTokPost, InstagramPost,
    Brand
)


def print_header(title):
    """헤더 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def check_amazon_data():
    """Amazon 랭킹 데이터 확인"""
    print_header("📦 Amazon 랭킹 데이터")

    with get_db_context() as db:
        # 전체 제품 수
        total_products = db.execute(select(func.count(AmazonProduct.id))).scalar()
        print(f"총 제품 수: {total_products}개")

        # Laneige 제품 수
        laneige_products = db.execute(
            select(func.count(AmazonProduct.id)).where(AmazonProduct.brand_id == 1)
        ).scalar()
        print(f"Laneige 제품: {laneige_products}개")

        # 총 랭킹 데이터 수 (시계열)
        total_rankings = db.execute(select(func.count(AmazonRanking.id))).scalar()
        print(f"총 랭킹 레코드: {total_rankings:,}개")

        # 최근 수집 시간
        latest_ranking = db.execute(
            select(AmazonRanking).order_by(desc(AmazonRanking.collected_at)).limit(1)
        ).scalar_one_or_none()

        if latest_ranking:
            print(f"마지막 수집: {latest_ranking.collected_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # 카테고리별 통계
        print("\n📊 카테고리별 수집 현황:")
        categories = db.execute(select(AmazonCategory)).scalars().all()
        for cat in categories:
            count = db.execute(
                select(func.count(AmazonRanking.id)).where(
                    AmazonRanking.category_id == cat.id
                )
            ).scalar()
            print(f"  - {cat.category_name}: {count:,}개 레코드")


def check_laneige_products():
    """Laneige 제품 상세 정보"""
    print_header("🎯 Laneige 제품 목록")

    with get_db_context() as db:
        products = db.execute(
            select(AmazonProduct).where(AmazonProduct.brand_id == 1).order_by(AmazonProduct.id)
        ).scalars().all()

        if not products:
            print("⚠️  Laneige 제품이 없습니다.")
            return

        print(f"총 {len(products)}개 제품:")
        print()

        for i, product in enumerate(products, 1):
            # 최근 랭킹 정보
            latest_ranking = db.execute(
                select(AmazonRanking)
                .where(AmazonRanking.product_id == product.id)
                .order_by(desc(AmazonRanking.collected_at))
                .limit(1)
            ).scalar_one_or_none()

            print(f"{i}. {product.product_name[:60]}")
            print(f"   ASIN: {product.asin}")
            if latest_ranking:
                print(f"   최근 순위: {latest_ranking.rank}위 (카테고리 ID: {latest_ranking.category_id})")
                if latest_ranking.price:
                    print(f"   가격: ${latest_ranking.price}")
                if latest_ranking.rating:
                    print(f"   평점: {latest_ranking.rating}★ ({latest_ranking.review_count or 0}개 리뷰)")
            print()


def check_events():
    """이벤트 발생 현황"""
    print_header("🎯 이벤트 발생 현황")

    with get_db_context() as db:
        # 전체 이벤트 수
        total_events = db.execute(select(func.count(RankingEvent.id))).scalar()
        print(f"총 이벤트: {total_events}개")

        if total_events == 0:
            print("\n⚠️  아직 감지된 이벤트가 없습니다.")
            print("   - 랭킹 데이터가 2회 이상 수집되어야 이벤트가 감지됩니다.")
            print("   - 1시간 후 다시 확인해보세요.")
            return

        # 심각도별 통계
        print("\n📊 심각도별 분류:")
        for severity in ['critical', 'high', 'medium', 'low']:
            count = db.execute(
                select(func.count(RankingEvent.id)).where(RankingEvent.severity == severity)
            ).scalar()
            if count > 0:
                emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[severity]
                print(f"  {emoji} {severity.upper()}: {count}개")

        # 이벤트 타입별 통계
        print("\n📊 이벤트 타입별:")
        event_types = db.execute(
            select(RankingEvent.event_type, func.count(RankingEvent.id))
            .group_by(RankingEvent.event_type)
        ).all()

        for event_type, count in event_types:
            print(f"  - {event_type}: {count}개")

        # 최근 이벤트 10개
        print("\n📋 최근 이벤트 (최대 10개):")
        recent_events = db.execute(
            select(RankingEvent)
            .order_by(desc(RankingEvent.detected_at))
            .limit(10)
        ).scalars().all()

        for i, event in enumerate(recent_events, 1):
            product = db.execute(
                select(AmazonProduct).where(AmazonProduct.id == event.product_id)
            ).scalar_one_or_none()

            print(f"\n{i}. [{event.severity.upper()}] {event.event_type}")
            if product:
                print(f"   제품: {product.product_name[:50]}")
            if event.rank_change:
                direction = "↑" if event.rank_change < 0 else "↓"
                print(f"   랭킹: {event.prev_rank}위 → {event.curr_rank}위 ({direction}{abs(event.rank_change)})")
            if event.price_change_pct:
                print(f"   가격 변동: {event.price_change_pct:+.1f}%")
            print(f"   감지 시간: {event.detected_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Context 수집: {'✅' if event.context_collected else '❌'}")
            print(f"   인사이트 생성: {'✅' if event.insight_generated else '❌'}")


def check_context_data():
    """Context 수집 데이터 확인"""
    print_header("🔍 Context 수집 데이터")

    with get_db_context() as db:
        # 소셜 미디어 컨텍스트
        social_count = db.execute(select(func.count(EventContextSocial.id))).scalar()
        print(f"소셜 미디어 컨텍스트: {social_count}개")

        if social_count > 0:
            # 플랫폼별
            print("\n  플랫폼별:")
            platforms = db.execute(
                select(EventContextSocial.platform, func.count(EventContextSocial.id))
                .group_by(EventContextSocial.platform)
            ).all()

            for platform, count in platforms:
                print(f"    - {platform}: {count}개")

            # 바이럴 컨텐츠
            viral_count = db.execute(
                select(func.count(EventContextSocial.id))
                .where(EventContextSocial.is_viral == True)
            ).scalar()
            print(f"\n  🔥 바이럴 컨텐츠: {viral_count}개")

        # 인사이트
        insight_count = db.execute(select(func.count(EventInsight.id))).scalar()
        print(f"\n💡 생성된 인사이트: {insight_count}개")

        if insight_count > 0:
            # 최근 인사이트
            recent_insight = db.execute(
                select(EventInsight).order_by(desc(EventInsight.generated_at)).limit(1)
            ).scalar_one_or_none()

            if recent_insight:
                print(f"\n  최근 인사이트:")
                print(f"    - 요약: {recent_insight.summary[:80]}...")
                print(f"    - 신뢰도: {recent_insight.confidence_score:.2f}")
                print(f"    - 모델: {recent_insight.llm_model}")
                print(f"    - 생성 시간: {recent_insight.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")


def check_social_media():
    """소셜 미디어 데이터 확인"""
    print_header("📱 소셜 미디어 수집 데이터")

    with get_db_context() as db:
        # YouTube
        youtube_count = db.execute(select(func.count(YouTubeVideo.id))).scalar()
        print(f"YouTube 영상: {youtube_count}개")

        if youtube_count > 0:
            latest_yt = db.execute(
                select(YouTubeVideo).order_by(desc(YouTubeVideo.last_collected_at)).limit(1)
            ).scalar_one_or_none()
            if latest_yt:
                print(f"  마지막 수집: {latest_yt.last_collected_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # TikTok
        tiktok_count = db.execute(select(func.count(TikTokPost.id))).scalar()
        print(f"\nTikTok 영상: {tiktok_count}개")

        if tiktok_count > 0:
            latest_tt = db.execute(
                select(TikTokPost).order_by(desc(TikTokPost.last_collected_at)).limit(1)
            ).scalar_one_or_none()
            if latest_tt:
                print(f"  마지막 수집: {latest_tt.last_collected_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # Instagram
        instagram_count = db.execute(select(func.count(InstagramPost.id))).scalar()
        print(f"\nInstagram 게시물: {instagram_count}개")

        if instagram_count > 0:
            latest_ig = db.execute(
                select(InstagramPost).order_by(desc(InstagramPost.last_collected_at)).limit(1)
            ).scalar_one_or_none()
            if latest_ig:
                print(f"  마지막 수집: {latest_ig.last_collected_at.strftime('%Y-%m-%d %H:%M:%S')}")

        total_social = youtube_count + tiktok_count + instagram_count
        if total_social == 0:
            print("\n💡 소셜 미디어 데이터 수집:")
            print("   python scripts/run_social.py")


def main():
    """메인 실행"""
    print("\n" + "=" * 80)
    print("  🔍 Laneige Ranking Tracker - 데이터 수집 현황")
    print("=" * 80)
    print(f"  조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. Amazon 데이터
        check_amazon_data()

        # 2. Laneige 제품
        check_laneige_products()

        # 3. 이벤트
        check_events()

        # 4. Context 데이터
        check_context_data()

        # 5. 소셜 미디어
        check_social_media()

        # 마무리
        print("\n" + "=" * 80)
        print("  ✅ 데이터 확인 완료")
        print("=" * 80)
        print()

    except Exception as e:
        logger.error(f"데이터 확인 중 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
