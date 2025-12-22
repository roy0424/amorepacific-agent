"""
이벤트 인사이트 생성기
RAG + LLM을 활용한 종합 분석 및 인사이트 생성
"""
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, List, Optional
import json
from datetime import datetime

from src.insights.vector_store import EventVectorStore
from src.insights.llm_client import ClaudeClient
from src.insights.prompts import PROMPT_VERSION
from src.models.events import RankingEvent, EventContextSocial, EventInsight
from src.models.amazon import AmazonProduct, AmazonCategory


class EventInsightGenerator:
    """이벤트 인사이트 생성기"""

    def __init__(self):
        """생성기 초기화"""
        self.vector_store = EventVectorStore()
        self.llm_client = ClaudeClient()
        logger.info("EventInsightGenerator 초기화 완료")

    def generate_insight(self, db: Session, event_id: int) -> Optional[EventInsight]:
        """
        특정 이벤트에 대한 인사이트 생성

        Args:
            db: DB 세션
            event_id: 이벤트 ID

        Returns:
            생성된 EventInsight 객체
        """
        logger.info(f"이벤트 {event_id} 인사이트 생성 시작")

        # 1. 이벤트 정보 로드
        event = db.execute(
            select(RankingEvent).where(RankingEvent.id == event_id)
        ).scalar_one_or_none()

        if not event:
            logger.error(f"이벤트 {event_id}를 찾을 수 없습니다")
            return None

        # 인사이트가 이미 생성되었는지 확인
        existing_insight = db.execute(
            select(EventInsight).where(EventInsight.event_id == event_id)
        ).scalar_one_or_none()

        if existing_insight:
            logger.info(f"이벤트 {event_id} 인사이트가 이미 존재합니다")
            return existing_insight

        # 2. 이벤트 데이터 준비
        event_data = self._prepare_event_data(db, event)

        # 3. 컨텍스트 데이터 수집
        context_data = self._collect_context_data(db, event)

        # 4. 유사 이벤트 검색 (RAG)
        similar_events = self._find_similar_events(event_data)

        # 5. LLM 인사이트 생성
        try:
            insight_result = self.llm_client.generate_structured_insight(
                event_data=event_data,
                context_data=context_data,
                similar_events=similar_events
            )
        except Exception as e:
            logger.error(f"LLM 인사이트 생성 실패: {e}")
            return None

        # 6. EventInsight 객체 생성 및 저장
        insight = EventInsight(
            event_id=event_id,
            summary=insight_result.get('summary', '인사이트 생성 실패'),
            analysis=insight_result.get('analysis', ''),
            likely_causes=json.dumps(insight_result.get('likely_causes', []), ensure_ascii=False),
            recommendations=json.dumps(insight_result.get('recommendations', []), ensure_ascii=False),
            similar_events=json.dumps([e['event_id'] for e in similar_events], ensure_ascii=False),
            similarity_scores=json.dumps([e['similarity_score'] for e in similar_events], ensure_ascii=False),
            llm_model=self.llm_client.model,
            prompt_version=PROMPT_VERSION,
            confidence_score=insight_result.get('confidence_score', 0.5),
            generated_at=datetime.utcnow()
        )

        db.add(insight)
        db.commit()
        db.refresh(insight)

        # 7. 이벤트를 벡터 DB에 추가 (향후 RAG 검색용)
        self._add_event_to_vector_store(event, event_data)

        # 8. 이벤트 상태 업데이트
        event.insight_generated = True
        db.commit()

        logger.info(f"이벤트 {event_id} 인사이트 생성 완료")
        return insight

    def _prepare_event_data(self, db: Session, event: RankingEvent) -> Dict:
        """이벤트 데이터 준비"""
        # 제품 정보 로드
        product = db.execute(
            select(AmazonProduct).where(AmazonProduct.id == event.product_id)
        ).scalar_one_or_none()

        # 카테고리 정보 로드
        category = db.execute(
            select(AmazonCategory).where(AmazonCategory.id == event.category_id)
        ).scalar_one_or_none()

        return {
            'event_id': event.id,
            'event_type': event.event_type,
            'severity': event.severity,
            'product_id': event.product_id,
            'product_name': product.product_name if product else 'Unknown',
            'category_id': event.category_id,
            'category_name': category.category_name if category else 'Unknown',
            'prev_rank': event.prev_rank,
            'curr_rank': event.curr_rank,
            'rank_change': event.rank_change,
            'rank_change_pct': event.rank_change_pct,
            'prev_price': float(event.prev_price) if event.prev_price else None,
            'curr_price': float(event.curr_price) if event.curr_price else None,
            'price_change_pct': event.price_change_pct,
            'prev_review_count': event.prev_review_count,
            'curr_review_count': event.curr_review_count,
            'review_change': event.review_change,
            'detected_at': event.detected_at.isoformat() if event.detected_at else None,
        }

    def _collect_context_data(self, db: Session, event: RankingEvent) -> Dict:
        """컨텍스트 데이터 수집"""
        context_data = {}

        # 소셜미디어 컨텍스트
        social_contexts = db.execute(
            select(EventContextSocial).where(EventContextSocial.event_id == event.id)
        ).scalars().all()

        context_data['social_media'] = [
            {
                'platform': ctx.platform,
                'content_id': ctx.content_id,
                'author': ctx.author,
                'text': ctx.text,
                'hashtags': ctx.hashtags,
                'view_count': ctx.view_count,
                'like_count': ctx.like_count,
                'comment_count': ctx.comment_count,
                'share_count': ctx.share_count,
                'engagement_score': ctx.engagement_score,
                'is_viral': ctx.is_viral,
                'posted_at': ctx.posted_at.isoformat() if ctx.posted_at else None,
            }
            for ctx in social_contexts
        ]

        # TODO: 리뷰 컨텍스트 수집
        context_data['reviews'] = []

        # TODO: 경쟁사 컨텍스트 수집
        context_data['competitors'] = []

        logger.debug(f"컨텍스트 데이터 수집 완료 - 소셜: {len(context_data['social_media'])}개")
        return context_data

    def _find_similar_events(self, event_data: Dict, top_k: int = 5) -> List[Dict]:
        """유사 이벤트 검색 (RAG)"""
        try:
            # 벡터 DB에 이벤트가 있는지 확인
            if self.vector_store.get_event_count() == 0:
                logger.info("벡터 DB에 이벤트가 없습니다 - 유사 이벤트 검색 스킵")
                return []

            # 유사 이벤트 검색
            similar_events = self.vector_store.search_similar_events(
                event_data=event_data,
                top_k=top_k
            )

            # 자기 자신 제외
            current_event_id = event_data.get('event_id')
            similar_events = [
                e for e in similar_events
                if e['event_id'] != current_event_id
            ]

            logger.info(f"유사 이벤트 {len(similar_events)}개 발견")
            return similar_events[:top_k]

        except Exception as e:
            logger.error(f"유사 이벤트 검색 실패: {e}")
            return []

    def _add_event_to_vector_store(self, event: RankingEvent, event_data: Dict):
        """이벤트를 벡터 DB에 추가"""
        try:
            self.vector_store.add_event(
                event_id=event.id,
                event_data=event_data,
                metadata={
                    'event_type': event.event_type,
                    'severity': event.severity,
                    'product_id': str(event.product_id),
                    'detected_at': event.detected_at.isoformat() if event.detected_at else None,
                }
            )
            logger.debug(f"이벤트 {event.id} 벡터 DB에 추가 완료")
        except Exception as e:
            logger.error(f"벡터 DB 추가 실패: {e}")

    def batch_generate_insights(
        self,
        db: Session,
        event_ids: Optional[List[int]] = None,
        limit: int = 10
    ) -> List[EventInsight]:
        """
        여러 이벤트에 대한 인사이트 일괄 생성

        Args:
            db: DB 세션
            event_ids: 이벤트 ID 목록 (None이면 미생성 이벤트 자동 선택)
            limit: 최대 생성 개수

        Returns:
            생성된 인사이트 목록
        """
        if event_ids is None:
            # 인사이트가 생성되지 않은 이벤트 중 critical/high만 선택
            events = db.execute(
                select(RankingEvent).where(
                    RankingEvent.insight_generated == False,
                    RankingEvent.severity.in_(['critical', 'high'])
                ).limit(limit)
            ).scalars().all()

            event_ids = [e.id for e in events]

        logger.info(f"일괄 인사이트 생성 시작 - {len(event_ids)}개 이벤트")

        insights = []
        for event_id in event_ids:
            try:
                insight = self.generate_insight(db, event_id)
                if insight:
                    insights.append(insight)
            except Exception as e:
                logger.error(f"이벤트 {event_id} 인사이트 생성 실패: {e}")
                continue

        logger.info(f"일괄 인사이트 생성 완료 - {len(insights)}개 성공")
        return insights
