"""
팀 회의용 데이터 리포트 생성기
수집된 데이터를 Excel 형태로 시각화하여 제공
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy import select, func, desc, and_
from loguru import logger

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.database import get_db_context
from src.models import (
    AmazonProduct, AmazonRanking, AmazonCategory, Brand,
    YouTubeVideo, TikTokPost, InstagramPost,
    RankingEvent, EventContextSocial
)
from config.settings import settings


class TeamReportGenerator:
    """팀 회의용 리포트 생성"""

    def __init__(self, output_path: str = None):
        """
        Args:
            output_path: 출력 경로 (None이면 data/reports 사용)
        """
        self.output_path = output_path or settings.REPORTS_DIR
        Path(self.output_path).mkdir(parents=True, exist_ok=True)

    def generate_full_report(self) -> str:
        """전체 리포트 생성"""
        logger.info("팀 회의용 리포트 생성 시작")

        # 파일명
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Laneige_Team_Report_{timestamp}.xlsx"
        filepath = Path(self.output_path) / filename

        # Excel Writer
        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            workbook = writer.book

            # 1. 요약 대시보드
            logger.info("요약 대시보드 생성 중...")
            self._create_summary_sheet(writer, workbook)

            # 2. Laneige 제품 현황
            logger.info("Laneige 제품 현황 생성 중...")
            self._create_laneige_products_sheet(writer, workbook)

            # 3. 랭킹 추이 (시계열)
            logger.info("랭킹 추이 생성 중...")
            self._create_ranking_trends_sheet(writer, workbook)

            # 4. 카테고리별 현황
            logger.info("카테고리별 현황 생성 중...")
            self._create_category_analysis_sheet(writer, workbook)

            # 5. 소셜 미디어 데이터
            logger.info("소셜 미디어 데이터 생성 중...")
            self._create_social_media_sheet(writer, workbook)

            # 6. 이벤트 현황
            logger.info("이벤트 현황 생성 중...")
            self._create_events_sheet(writer, workbook)

            # 7. 시스템 설정
            logger.info("시스템 설정 생성 중...")
            self._create_system_config_sheet(writer, workbook)

            # 8. Raw 데이터
            logger.info("Raw 데이터 생성 중...")
            self._create_raw_data_sheet(writer, workbook)

        logger.success(f"리포트 생성 완료: {filepath}")
        return str(filepath)

    def _create_summary_sheet(self, writer, workbook):
        """요약 대시보드"""
        with get_db_context() as db:
            # 통계 수집
            total_products = db.execute(select(func.count(AmazonProduct.id))).scalar()
            laneige_products = db.execute(
                select(func.count(AmazonProduct.id)).where(AmazonProduct.brand_id == 1)
            ).scalar()
            total_rankings = db.execute(select(func.count(AmazonRanking.id))).scalar()
            total_events = db.execute(select(func.count(RankingEvent.id))).scalar()

            youtube_count = db.execute(select(func.count(YouTubeVideo.id))).scalar()
            tiktok_count = db.execute(select(func.count(TikTokPost.id))).scalar()
            instagram_count = db.execute(select(func.count(InstagramPost.id))).scalar()

            # 최근 수집 시간
            latest_ranking = db.execute(
                select(AmazonRanking).order_by(desc(AmazonRanking.collected_at)).limit(1)
            ).scalar_one_or_none()

            latest_youtube = db.execute(
                select(YouTubeVideo).order_by(desc(YouTubeVideo.last_collected_at)).limit(1)
            ).scalar_one_or_none()

            # 데이터 프레임 생성
            summary_data = {
                '항목': [
                    '📊 데이터 수집 현황',
                    '총 Amazon 제품 수',
                    'Laneige 제품 수',
                    '총 랭킹 레코드',
                    '마지막 랭킹 수집',
                    '',
                    '📱 소셜 미디어',
                    'YouTube 영상',
                    'TikTok 포스트',
                    'Instagram 포스트',
                    '마지막 소셜 수집',
                    '',
                    '🎯 이벤트 분석',
                    '감지된 이벤트',
                    '이벤트 상태',
                    '',
                    '⚙️ 시스템',
                    '자동 수집 스케줄',
                    '이벤트 감지 방식',
                    '다음 수집 예정',
                ],
                '값': [
                    '',
                    f'{total_products:,}개',
                    f'{laneige_products}개',
                    f'{total_rankings:,}개',
                    latest_ranking.collected_at.strftime('%Y-%m-%d %H:%M:%S') if latest_ranking else 'N/A',
                    '',
                    '',
                    f'{youtube_count}개',
                    f'{tiktok_count}개',
                    f'{instagram_count}개',
                    latest_youtube.last_collected_at.strftime('%Y-%m-%d %H:%M:%S') if latest_youtube else 'N/A',
                    '',
                    '',
                    f'{total_events}개',
                    '정상 (12시간 트렌드 분석)' if total_events > 0 else '대기 중 (데이터 축적 필요)',
                    '',
                    '',
                    '1시간마다 (Amazon 랭킹)',
                    '트렌드 기반 + 구간별 임계값',
                    (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:00'),
                ]
            }

            df = pd.DataFrame(summary_data)

            # 시트 작성
            df.to_excel(writer, sheet_name='📊 요약', index=False)

            # 포맷팅
            worksheet = writer.sheets['📊 요약']
            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 40)

            # 헤더 포맷
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })

            # 섹션 헤더 포맷
            section_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D9E1F2',
                'border': 1
            })

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # 섹션 하이라이트
            section_rows = [1, 7, 13, 17]
            for row in section_rows:
                worksheet.write(row, 0, df.iloc[row]['항목'], section_format)
                worksheet.write(row, 1, df.iloc[row]['값'], section_format)

    def _create_laneige_products_sheet(self, writer, workbook):
        """Laneige 제품 현황"""
        with get_db_context() as db:
            products = db.execute(
                select(AmazonProduct).where(AmazonProduct.brand_id == 1)
            ).scalars().all()

            data = []
            for product in products:
                # 최근 랭킹
                latest_ranking = db.execute(
                    select(AmazonRanking)
                    .where(AmazonRanking.product_id == product.id)
                    .order_by(desc(AmazonRanking.collected_at))
                    .limit(1)
                ).scalar_one_or_none()

                # 24시간 전 랭킹
                cutoff = datetime.now() - timedelta(hours=24)
                old_ranking = db.execute(
                    select(AmazonRanking)
                    .where(and_(
                        AmazonRanking.product_id == product.id,
                        AmazonRanking.collected_at <= cutoff
                    ))
                    .order_by(desc(AmazonRanking.collected_at))
                    .limit(1)
                ).scalar_one_or_none()

                # 카테고리
                category = None
                if latest_ranking:
                    category = db.execute(
                        select(AmazonCategory).where(AmazonCategory.id == latest_ranking.category_id)
                    ).scalar_one_or_none()

                # 24시간 변동
                rank_change_24h = None
                if latest_ranking and old_ranking:
                    rank_change_24h = old_ranking.rank - latest_ranking.rank

                data.append({
                    '제품명': product.product_name,
                    'ASIN': product.asin,
                    '카테고리': category.category_name if category else 'N/A',
                    '현재 순위': latest_ranking.rank if latest_ranking else 'N/A',
                    '24시간 변동': rank_change_24h if rank_change_24h else 0,
                    '현재 가격': f"${latest_ranking.price:,.2f}" if latest_ranking and latest_ranking.price else 'N/A',
                    '평점': f"{latest_ranking.rating:.1f}★" if latest_ranking and latest_ranking.rating else 'N/A',
                    '리뷰 수': f"{latest_ranking.review_count:,}" if latest_ranking and latest_ranking.review_count else 'N/A',
                    '마지막 수집': latest_ranking.collected_at.strftime('%m/%d %H:%M') if latest_ranking else 'N/A',
                    '제품 URL': product.product_url or ''
                })

            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='🎯 Laneige 제품', index=False)

            # 포맷팅
            worksheet = writer.sheets['🎯 Laneige 제품']
            worksheet.set_column('A:A', 50)  # 제품명
            worksheet.set_column('B:B', 12)  # ASIN
            worksheet.set_column('C:C', 20)  # 카테고리
            worksheet.set_column('D:D', 12)  # 현재 순위
            worksheet.set_column('E:E', 12)  # 24시간 변동
            worksheet.set_column('F:F', 12)  # 가격
            worksheet.set_column('G:G', 10)  # 평점
            worksheet.set_column('H:H', 12)  # 리뷰 수
            worksheet.set_column('I:I', 15)  # 마지막 수집
            worksheet.set_column('J:J', 60)  # URL

            # 조건부 서식 - 순위 변동
            green_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
            red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})

            # 헤더
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

    def _create_ranking_trends_sheet(self, writer, workbook):
        """랭킹 추이 (시계열)"""
        with get_db_context() as db:
            # Laneige 제품들의 최근 7일 랭킹
            cutoff = datetime.now() - timedelta(days=7)

            products = db.execute(
                select(AmazonProduct).where(AmazonProduct.brand_id == 1)
            ).scalars().all()

            all_data = []

            for product in products:
                rankings = db.execute(
                    select(AmazonRanking)
                    .where(and_(
                        AmazonRanking.product_id == product.id,
                        AmazonRanking.collected_at >= cutoff
                    ))
                    .order_by(AmazonRanking.collected_at)
                ).scalars().all()

                for ranking in rankings:
                    category = db.execute(
                        select(AmazonCategory).where(AmazonCategory.id == ranking.category_id)
                    ).scalar_one_or_none()

                    all_data.append({
                        '수집 시간': ranking.collected_at,
                        '제품명': product.product_name[:50],
                        'ASIN': product.asin,
                        '카테고리': category.category_name if category else 'N/A',
                        '순위': ranking.rank,
                        '가격': ranking.price,
                        '평점': ranking.rating,
                        '리뷰 수': ranking.review_count
                    })

            df = pd.DataFrame(all_data)

            if not df.empty:
                df = df.sort_values(['제품명', '수집 시간'])

            df.to_excel(writer, sheet_name='📈 랭킹 추이', index=False)

            # 포맷팅
            worksheet = writer.sheets['📈 랭킹 추이']
            worksheet.set_column('A:A', 20)  # 수집 시간
            worksheet.set_column('B:B', 50)  # 제품명
            worksheet.set_column('C:C', 12)  # ASIN
            worksheet.set_column('D:D', 20)  # 카테고리
            worksheet.set_column('E:E', 10)  # 순위
            worksheet.set_column('F:F', 10)  # 가격
            worksheet.set_column('G:G', 10)  # 평점
            worksheet.set_column('H:H', 12)  # 리뷰 수

            # 헤더
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

    def _create_category_analysis_sheet(self, writer, workbook):
        """카테고리별 현황"""
        with get_db_context() as db:
            categories = db.execute(select(AmazonCategory)).scalars().all()

            data = []
            for cat in categories:
                # 총 레코드 수
                total_records = db.execute(
                    select(func.count(AmazonRanking.id))
                    .where(AmazonRanking.category_id == cat.id)
                ).scalar()

                # Laneige 제품 수
                laneige_count = db.execute(
                    select(func.count(AmazonRanking.id.distinct()))
                    .join(AmazonProduct)
                    .where(and_(
                        AmazonRanking.category_id == cat.id,
                        AmazonProduct.brand_id == 1
                    ))
                ).scalar()

                # 최근 수집
                latest = db.execute(
                    select(AmazonRanking)
                    .where(AmazonRanking.category_id == cat.id)
                    .order_by(desc(AmazonRanking.collected_at))
                    .limit(1)
                ).scalar_one_or_none()

                data.append({
                    '카테고리': cat.category_name,
                    '총 레코드 수': f"{total_records:,}",
                    'Laneige 제품 수': laneige_count,
                    '마지막 수집': latest.collected_at.strftime('%Y-%m-%d %H:%M') if latest else 'N/A',
                    'URL': cat.category_url or ''
                })

            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='📂 카테고리별', index=False)

            # 포맷팅
            worksheet = writer.sheets['📂 카테고리별']
            worksheet.set_column('A:A', 30)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 15)
            worksheet.set_column('D:D', 20)
            worksheet.set_column('E:E', 60)

    def _create_social_media_sheet(self, writer, workbook):
        """소셜 미디어 데이터"""
        with get_db_context() as db:
            from src.models.social_media import YouTubeMetric, TikTokMetric

            # YouTube - 최신 메트릭을 서브쿼리로 조회
            youtube_videos = db.execute(select(YouTubeVideo).limit(50)).scalars().all()

            youtube_data = []
            for video in youtube_videos:
                # 최신 메트릭 조회
                latest_metric = db.execute(
                    select(YouTubeMetric)
                    .where(YouTubeMetric.video_id == video.id)
                    .order_by(desc(YouTubeMetric.collected_at))
                    .limit(1)
                ).scalar_one_or_none()

                youtube_data.append({
                    '플랫폼': 'YouTube',
                    '제목': video.title[:80],
                    '채널': video.channel_title,
                    '조회수': f"{latest_metric.view_count:,}" if latest_metric and latest_metric.view_count else 'N/A',
                    '좋아요': f"{latest_metric.like_count:,}" if latest_metric and latest_metric.like_count else 'N/A',
                    '댓글': f"{latest_metric.comment_count:,}" if latest_metric and latest_metric.comment_count else 'N/A',
                    '게시일': video.published_at.strftime('%Y-%m-%d') if video.published_at else 'N/A',
                    '수집일': video.last_collected_at.strftime('%Y-%m-%d %H:%M') if video.last_collected_at else 'N/A',
                    'URL': f"https://youtube.com/watch?v={video.video_id}",
                    '_view_count_sort': latest_metric.view_count if latest_metric and latest_metric.view_count else 0
                })

            # TikTok - 최신 메트릭을 서브쿼리로 조회
            tiktok_posts = db.execute(select(TikTokPost).limit(50)).scalars().all()

            tiktok_data = []
            for post in tiktok_posts:
                # 최신 메트릭 조회
                latest_metric = db.execute(
                    select(TikTokMetric)
                    .where(TikTokMetric.post_id == post.id)
                    .order_by(desc(TikTokMetric.collected_at))
                    .limit(1)
                ).scalar_one_or_none()

                tiktok_data.append({
                    '플랫폼': 'TikTok',
                    '제목': post.description[:80] if post.description else 'No description',
                    '채널': post.author_username,
                    '조회수': f"{latest_metric.view_count:,}" if latest_metric and latest_metric.view_count else 'N/A',
                    '좋아요': f"{latest_metric.like_count:,}" if latest_metric and latest_metric.like_count else 'N/A',
                    '댓글': f"{latest_metric.comment_count:,}" if latest_metric and latest_metric.comment_count else 'N/A',
                    '게시일': post.posted_at.strftime('%Y-%m-%d') if post.posted_at else 'N/A',
                    '수집일': post.last_collected_at.strftime('%Y-%m-%d %H:%M') if post.last_collected_at else 'N/A',
                    'URL': post.video_url or 'N/A',
                    '_view_count_sort': latest_metric.view_count if latest_metric and latest_metric.view_count else 0
                })

            # 합치기
            all_data = youtube_data + tiktok_data
            df = pd.DataFrame(all_data)

            if not df.empty:
                # 조회수 기준 정렬 (내림차순)
                df = df.sort_values('_view_count_sort', ascending=False)
                # 정렬용 컬럼 제거
                df = df.drop(columns=['_view_count_sort'])

            df.to_excel(writer, sheet_name='📱 소셜미디어', index=False)

            # 포맷팅
            worksheet = writer.sheets['📱 소셜미디어']
            worksheet.set_column('A:A', 10)  # 플랫폼
            worksheet.set_column('B:B', 60)  # 제목
            worksheet.set_column('C:C', 20)  # 채널
            worksheet.set_column('D:D', 12)  # 조회수
            worksheet.set_column('E:E', 12)  # 좋아요
            worksheet.set_column('F:F', 10)  # 댓글
            worksheet.set_column('G:G', 12)  # 게시일
            worksheet.set_column('H:H', 18)  # 수집일
            worksheet.set_column('I:I', 50)  # URL

    def _create_events_sheet(self, writer, workbook):
        """이벤트 현황"""
        with get_db_context() as db:
            events = db.execute(
                select(RankingEvent)
                .order_by(desc(RankingEvent.detected_at))
                .limit(100)
            ).scalars().all()

            data = []
            for event in events:
                product = db.execute(
                    select(AmazonProduct).where(AmazonProduct.id == event.product_id)
                ).scalar_one_or_none()

                category = db.execute(
                    select(AmazonCategory).where(AmazonCategory.id == event.category_id)
                ).scalar_one_or_none()

                data.append({
                    '감지 시간': event.detected_at.strftime('%Y-%m-%d %H:%M:%S'),
                    '제품명': product.product_name[:50] if product else 'N/A',
                    'ASIN': product.asin if product else 'N/A',
                    '카테고리': category.category_name if category else 'N/A',
                    '이벤트 타입': event.event_type,
                    '심각도': event.severity,
                    '이전 순위': event.prev_rank,
                    '현재 순위': event.curr_rank,
                    '순위 변동': event.rank_change,
                    '가격 변동(%)': f"{event.price_change_pct:.1f}" if event.price_change_pct else 'N/A',
                    'Context 수집': '✓' if event.context_collected else '✗',
                    '인사이트 생성': '✓' if event.insight_generated else '✗',
                })

            if data:
                df = pd.DataFrame(data)
            else:
                # 이벤트가 없을 때
                df = pd.DataFrame({
                    '상태': ['아직 이벤트가 감지되지 않았습니다.'],
                    '설명': ['랭킹 데이터가 12시간 이상 축적되면 트렌드 기반 이벤트 감지가 시작됩니다.']
                })

            df.to_excel(writer, sheet_name='🎯 이벤트', index=False)

            worksheet = writer.sheets['🎯 이벤트']
            for i in range(len(df.columns)):
                worksheet.set_column(i, i, 18)

    def _create_system_config_sheet(self, writer, workbook):
        """시스템 설정"""
        config_data = {
            '설정 항목': [
                '== 데이터 수집 ==',
                'Amazon 수집 주기',
                '수집할 제품 수',
                '수집 카테고리 수',
                '',
                '== 이벤트 감지 ==',
                '감지 방식',
                '트렌드 분석 시간',
                '최소 데이터 포인트',
                '일관성 임계값',
                '',
                '순위 구간별 임계값:',
                '1-5위 (초상위권)',
                '6-10위 (상위권)',
                '11-20위 (중상위권)',
                '21-30위 (중위권)',
                '31-50위 (중하위권)',
                '51-100위 (하위권)',
                '',
                '== 프롬프트 테스팅 ==',
                '사용 가능한 템플릿',
                '기본 LLM 모델',
                '',
                '== 데이터 저장 ==',
                'Database',
                '리포트 경로',
                '백업 경로',
            ],
            '값': [
                '',
                f'{settings.AMAZON_SCRAPE_INTERVAL_HOURS}시간마다',
                f'{settings.AMAZON_MAX_PRODUCTS_PER_CATEGORY}개/카테고리',
                f'{len(settings.AMAZON_CATEGORIES)}개',
                '',
                '',
                '트렌드 기반 + 구간별 임계값',
                f'{settings.EVENT_TREND_ANALYSIS_HOURS}시간',
                f'{settings.EVENT_TREND_MIN_DATA_POINTS}개',
                f'{settings.EVENT_TREND_CONSISTENCY_THRESHOLD * 100}%',
                '',
                '',
                '±2위 변동 시 이벤트',
                '±3위 변동 시 이벤트',
                '±5위 변동 시 이벤트',
                '±7위 변동 시 이벤트',
                '±10위 변동 시 이벤트',
                '±15위 변동 시 이벤트',
                '',
                '',
                '6개 (basic, detailed, marketing, competitive, data-driven, bullet)',
                'gpt-4o (OpenAI)',
                '',
                '',
                settings.DATABASE_URL,
                str(settings.REPORTS_DIR),
                str(settings.BACKUPS_DIR),
            ]
        }

        df = pd.DataFrame(config_data)
        df.to_excel(writer, sheet_name='⚙️ 시스템 설정', index=False)

        worksheet = writer.sheets['⚙️ 시스템 설정']
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 60)

    def _create_raw_data_sheet(self, writer, workbook):
        """Raw 데이터 (최근 1000개 레코드)"""
        with get_db_context() as db:
            rankings = db.execute(
                select(AmazonRanking)
                .order_by(desc(AmazonRanking.collected_at))
                .limit(1000)
            ).scalars().all()

            data = []
            for ranking in rankings:
                product = db.execute(
                    select(AmazonProduct).where(AmazonProduct.id == ranking.product_id)
                ).scalar_one_or_none()

                category = db.execute(
                    select(AmazonCategory).where(AmazonCategory.id == ranking.category_id)
                ).scalar_one_or_none()

                brand = None
                if product and product.brand_id:
                    brand = db.execute(
                        select(Brand).where(Brand.id == product.brand_id)
                    ).scalar_one_or_none()

                data.append({
                    '수집 시간': ranking.collected_at,
                    '브랜드': brand.name if brand else 'Unknown',
                    '제품명': product.product_name if product else 'N/A',
                    'ASIN': product.asin if product else 'N/A',
                    '카테고리': category.category_name if category else 'N/A',
                    '순위': ranking.rank,
                    '가격': ranking.price,
                    '평점': ranking.rating,
                    '리뷰 수': ranking.review_count,
                })

            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='📋 Raw Data', index=False)

            worksheet = writer.sheets['📋 Raw Data']
            for i in range(len(df.columns)):
                worksheet.set_column(i, i, 18)


def main():
    """메인 실행"""
    print("=" * 80)
    print("  📊 팀 회의용 데이터 리포트 생성")
    print("=" * 80)
    print()

    try:
        generator = TeamReportGenerator()
        filepath = generator.generate_full_report()

        print()
        print("=" * 80)
        print("  ✅ 리포트 생성 완료!")
        print("=" * 80)
        print()
        print(f"📄 파일 위치: {filepath}")
        print()
        print("📊 포함된 시트:")
        print("  1. 📊 요약 - 전체 데이터 수집 현황")
        print("  2. 🎯 Laneige 제품 - 제품별 현황 및 24시간 변동")
        print("  3. 📈 랭킹 추이 - 최근 7일 시계열 데이터")
        print("  4. 📂 카테고리별 - 카테고리별 통계")
        print("  5. 📱 소셜미디어 - YouTube/TikTok Top 컨텐츠")
        print("  6. 🎯 이벤트 - 감지된 이벤트 목록")
        print("  7. ⚙️ 시스템 설정 - 현재 설정값")
        print("  8. 📋 Raw Data - 최근 1000개 레코드")
        print()
        print("=" * 80)

    except Exception as e:
        logger.error(f"리포트 생성 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
