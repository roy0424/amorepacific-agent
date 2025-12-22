"""
랭킹 이벤트 감지 로직 (개선된 버전)

주요 개선사항:
1. 트렌드 기반 분석 (최근 N시간 데이터 분석)
2. 순위 구간별 차등 임계값 (상위권 민감도 높임)
3. 카테고리별 독립 분석
4. 중복 이벤트 방지
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_
from loguru import logger

from src.models.amazon import AmazonRanking, AmazonProduct, AmazonCategory
from src.models.events import RankingEvent


class EventDetector:
    """트렌드 기반 랭킹 이벤트 감지"""

    def __init__(
        self,
        trend_analysis_hours: int = 12,
        trend_min_data_points: int = 3,
        trend_consistency_threshold: float = 0.6,
        trend_windows_hours: Optional[List[int]] = None,
        surge_window_hours: Optional[int] = None,
        steady_window_hours: Optional[int] = None,
        steady_consistency_min: Optional[float] = None,
        rank_thresholds: dict = None,
        rank_change_pct_threshold: float = 30.0,
        use_hybrid_threshold: bool = True,
        price_change_pct_threshold: float = 20.0,
        review_surge_threshold: int = 100,
        product_model=AmazonProduct,
        ranking_model=AmazonRanking,
        event_model=RankingEvent,
        target_brand_id: int = 1
    ):
        from config.settings import settings

        if trend_windows_hours is None:
            default_window_hours = getattr(settings, "EVENT_TREND_WINDOWS_HOURS", None)
            default_analysis_hours = getattr(settings, "EVENT_TREND_ANALYSIS_HOURS", None)
            if (
                trend_analysis_hours is not None
                and default_analysis_hours is not None
                and trend_analysis_hours != default_analysis_hours
            ):
                trend_windows_hours = [trend_analysis_hours]
            else:
                trend_windows_hours = default_window_hours
        if not trend_windows_hours:
            trend_windows_hours = [trend_analysis_hours]
        self.trend_windows_hours = sorted(set(int(h) for h in trend_windows_hours))
        self.trend_analysis_hours = max(self.trend_windows_hours)
        self.trend_min_data_points = trend_min_data_points
        self.trend_consistency_threshold = trend_consistency_threshold
        self.surge_window_hours = (
            int(surge_window_hours)
            if surge_window_hours is not None
            else int(getattr(settings, "EVENT_SURGE_WINDOW_HOURS", self.trend_windows_hours[0]))
        )
        self.steady_window_hours = (
            int(steady_window_hours)
            if steady_window_hours is not None
            else int(getattr(settings, "EVENT_STEADY_WINDOW_HOURS", self.trend_analysis_hours))
        )
        self.steady_consistency_min = (
            float(steady_consistency_min)
            if steady_consistency_min is not None
            else float(getattr(settings, "EVENT_STEADY_CONSISTENCY_MIN", 0.8))
        )
        self.rank_thresholds = rank_thresholds or {}
        self.rank_change_pct_threshold = rank_change_pct_threshold
        self.use_hybrid_threshold = use_hybrid_threshold
        self.price_change_pct_threshold = price_change_pct_threshold
        self.review_surge_threshold = review_surge_threshold
        self.product_model = product_model
        self.ranking_model = ranking_model
        self.event_model = event_model
        self.target_brand_id = target_brand_id

    def detect_events(
        self,
        db: Session,
        lookback_hours: Optional[int] = None
    ) -> List[RankingEvent]:
        """
        이벤트 감지 (트렌드 분석 기반)

        Args:
            db: Database session
            lookback_hours: 사용 안함 (하위 호환성 유지)

        Returns:
            감지된 이벤트 목록
        """
        logger.info(
            "트렌드 기반 이벤트 감지 시작 "
            f"(분석 범위: {self.trend_analysis_hours}시간, "
            f"창: {self.trend_windows_hours})"
        )

        events = []

        # Laneige 제품 조회
        laneige_products = db.execute(
            select(self.product_model).where(self.product_model.brand_id == self.target_brand_id)
        ).scalars().all()

        logger.info(f"Laneige 제품 {len(laneige_products)}개 발견")

        for product in laneige_products:
            # 카테고리별로 이벤트 감지
            product_events = self._detect_product_events_by_category(db, product)
            events.extend(product_events)

        logger.info(f"총 {len(events)}개 이벤트 감지됨")
        return events

    def _detect_product_events_by_category(
        self,
        db: Session,
        product: Any
    ) -> List[RankingEvent]:
        """카테고리별 이벤트 감지"""

        events = []

        # 제품이 속한 카테고리 목록 조회
        categories = db.execute(
            select(self.ranking_model.category_id)
            .where(self.ranking_model.product_id == product.id)
            .distinct()
        ).scalars().all()

        for category_id in categories:
            # 카테고리별로 독립적으로 분석
            category_events = self._analyze_category_trend(db, product, category_id)
            events.extend(category_events)

        return events

    def _analyze_category_trend(
        self,
        db: Session,
        product: Any,
        category_id: int
    ) -> List[RankingEvent]:
        """특정 카테고리에서의 트렌드 분석"""

        events = []
        from config.settings import settings

        now = datetime.utcnow()
        cutoff_time = now - timedelta(
            hours=self.trend_analysis_hours + settings.AMAZON_SCRAPE_INTERVAL_HOURS
        )

        # 최근 N시간 내 랭킹 데이터 조회 (카테고리별)
        rankings = db.execute(
            select(self.ranking_model)
            .where(
                and_(
                    self.ranking_model.product_id == product.id,
                    self.ranking_model.category_id == category_id,
                    self.ranking_model.collected_at >= cutoff_time
                )
            )
            .order_by(desc(self.ranking_model.collected_at))
        ).scalars().all()

        if len(rankings) < self.trend_min_data_points:
            # 데이터 부족
            return events

        now = rankings[0].collected_at
        trend_map = self._calculate_trends_by_window(rankings, now)
        selection = self._select_trend_for_event(trend_map)
        if not selection:
            return events
        selected_trend, event_type = selection

        # 순위 변동 이벤트 감지
        rank_event = self._build_rank_event(
            db, product, category_id, selected_trend, event_type
        )
        if rank_event:
            events.append(rank_event)

        # 최신 2개 데이터로 가격/리뷰 변동 체크 (기존 방식 유지)
        if len(rankings) >= 2:
            current = rankings[0]
            previous = rankings[1]

            # 가격 변동
            price_event = self._check_price_change(product, category_id, current, previous)
            if price_event:
                events.append(price_event)

            # 리뷰 급증
            review_event = self._check_review_surge(product, category_id, current, previous)
            if review_event:
                events.append(review_event)

            # 재고 변화
            stock_event = self._check_stock_change(product, category_id, current, previous)
            if stock_event:
                events.append(stock_event)

        return events

    def _calculate_trends_by_window(
        self,
        rankings: List[Any],
        now: datetime
    ) -> Dict[int, Dict[str, Any]]:
        trends = {}
        for window_hours in self.trend_windows_hours:
            window_cutoff = now - timedelta(hours=window_hours)
            window_rankings = [
                r for r in rankings
                if r.collected_at >= window_cutoff
            ]
            if len(window_rankings) < self.trend_min_data_points:
                continue
            trend = self._calculate_trend(window_rankings)
            if trend:
                trends[window_hours] = trend
        return trends

    def _select_trend_for_event(
        self,
        trend_map: Dict[int, Dict[str, Any]]
    ) -> Optional[Tuple[Dict[str, Any], str]]:
        if not trend_map:
            return None

        steady_trend = trend_map.get(self.steady_window_hours)
        if steady_trend and self._trend_meets_thresholds(steady_trend):
            if steady_trend['consistency'] >= self.steady_consistency_min:
                event_type = (
                    "STEADY_RISE" if steady_trend['total_change'] > 0 else "STEADY_DECLINE"
                )
                return steady_trend, event_type

        surge_trend = trend_map.get(self.surge_window_hours)
        if surge_trend and self._trend_meets_thresholds(surge_trend):
            event_type = (
                "RANK_SURGE" if surge_trend['total_change'] > 0 else "RANK_DROP"
            )
            return surge_trend, event_type

        candidates = [
            (window, trend)
            for window, trend in trend_map.items()
            if self._trend_meets_thresholds(trend)
        ]
        if not candidates:
            return None

        window, trend = max(candidates, key=lambda item: item[0])
        if trend['consistency'] >= self.steady_consistency_min:
            event_type = "STEADY_RISE" if trend['total_change'] > 0 else "STEADY_DECLINE"
        else:
            event_type = "RANK_SURGE" if trend['total_change'] > 0 else "RANK_DROP"
        return trend, event_type

    def _trend_meets_thresholds(self, trend: Dict[str, Any]) -> bool:
        total_change = trend['total_change']
        start_rank = trend['start_rank']
        end_rank = trend['end_rank']
        consistency = trend['consistency']

        if consistency < self.trend_consistency_threshold:
            return False

        abs_threshold = self._get_rank_threshold(end_rank)
        if abs(total_change) >= abs_threshold:
            return True

        if self.use_hybrid_threshold and start_rank > 0:
            change_pct = abs(total_change) / start_rank * 100
            if change_pct >= self.rank_change_pct_threshold:
                return True

        return False

    def _calculate_trend(self, rankings: List[Any]) -> Optional[Dict]:
        """
        트렌드 계산

        Returns:
            {
                'direction': 'rising' | 'falling' | 'stable',
                'total_change': int,
                'start_rank': int,
                'end_rank': int,
                'consistency': float,  # 0-1
                'avg_change_per_hour': float,
                'is_significant': bool
            }
        """
        if len(rankings) < 2:
            return None

        # 시간순 정렬 (오래된 것부터)
        sorted_rankings = sorted(rankings, key=lambda r: r.collected_at)

        start_rank = sorted_rankings[0].rank
        end_rank = sorted_rankings[-1].rank
        total_change = start_rank - end_rank  # 양수면 상승(순위 감소), 음수면 하락(순위 증가)

        # 방향성 일관성 계산
        direction_changes = []
        for i in range(1, len(sorted_rankings)):
            prev_rank = sorted_rankings[i - 1].rank
            curr_rank = sorted_rankings[i].rank
            change = prev_rank - curr_rank

            if change != 0:
                direction_changes.append(1 if change > 0 else -1)

        if not direction_changes:
            return None

        # 일관성: 같은 방향으로 움직인 비율
        primary_direction = 1 if total_change > 0 else -1
        consistent_count = sum(1 for d in direction_changes if d == primary_direction)
        consistency = consistent_count / len(direction_changes)

        # 시간당 평균 변동
        time_span = (sorted_rankings[-1].collected_at - sorted_rankings[0].collected_at).total_seconds() / 3600
        avg_change_per_hour = abs(total_change) / time_span if time_span > 0 else 0

        return {
            'direction': 'rising' if total_change > 0 else 'falling' if total_change < 0 else 'stable',
            'total_change': total_change,
            'start_rank': start_rank,
            'end_rank': end_rank,
            'consistency': consistency,
            'avg_change_per_hour': avg_change_per_hour,
            'data_points': len(sorted_rankings)
        }

    def _get_rank_threshold(self, rank: int) -> int:
        """순위에 따른 임계값 반환 (구간별)"""
        for tier, config in self.rank_thresholds.items():
            min_rank, max_rank = config['range']
            if min_rank <= rank <= max_rank:
                return config['threshold']

        # 100위 초과는 하위권으로 처리
        return 15

    def _build_rank_event(
        self,
        db: Session,
        product: Any,
        category_id: int,
        trend: Dict,
        event_type: str
    ) -> Optional[RankingEvent]:
        """트렌드 기반 순위 변동 이벤트 감지"""

        total_change = trend['total_change']
        start_rank = trend['start_rank']
        end_rank = trend['end_rank']
        consistency = trend['consistency']

        if not self._trend_meets_thresholds(trend):
            return None

        # 심각도 계산
        severity = self._calculate_severity(abs(total_change), end_rank, consistency)

        # 시간 윈도우 계산
        from config.settings import settings
        detected_at = datetime.utcnow()
        time_window_start = detected_at - timedelta(days=settings.EVENT_LOOKBACK_DAYS)
        time_window_end = detected_at + timedelta(days=settings.EVENT_LOOKFORWARD_DAYS)

        # 이벤트 생성
        event = self.event_model(
            product_id=product.id,
            category_id=category_id,
            event_type=event_type,
            severity=severity,
            prev_rank=start_rank,
            curr_rank=end_rank,
            rank_change=end_rank - start_rank,  # 양수면 하락, 음수면 상승
            rank_change_pct=abs(total_change) / start_rank * 100 if start_rank > 0 else None,
            detected_at=detected_at,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            context_collected=False,
            insight_generated=False
        )

        logger.info(
            f"이벤트 감지: {event_type} - {product.product_name[:30]}... "
            f"({start_rank}위 → {end_rank}위, 일관성: {consistency:.2f})"
        )

        return event

    def _calculate_severity(self, change_amount: int, current_rank: int, consistency: float) -> str:
        """
        심각도 계산

        고려 요소:
        1. 변동 크기 (절대값)
        2. 현재 순위 (상위권일수록 중요)
        3. 트렌드 일관성 (높을수록 신뢰도 높음)
        """
        # 기본 점수 (0-100)
        score = 0

        # 1. 변동 크기 (최대 40점)
        if change_amount >= 20:
            score += 40
        elif change_amount >= 15:
            score += 30
        elif change_amount >= 10:
            score += 20
        elif change_amount >= 5:
            score += 10

        # 2. 순위 위치 (최대 40점)
        if current_rank <= 5:
            score += 40  # 초상위권
        elif current_rank <= 10:
            score += 30  # 상위권
        elif current_rank <= 20:
            score += 20  # 중상위권
        elif current_rank <= 30:
            score += 10  # 중위권

        # 3. 일관성 (최대 20점)
        score += int(consistency * 20)

        # 심각도 결정
        if score >= 80:
            return 'critical'
        elif score >= 60:
            return 'high'
        elif score >= 40:
            return 'medium'
        else:
            return 'low'

    def _check_price_change(
        self,
        product: Any,
        category_id: int,
        current: Any,
        previous: Any
    ) -> Optional[RankingEvent]:
        """가격 변동 체크 (기존 로직 유지)"""

        if not current.price or not previous.price:
            return None

        price_change = float(current.price) - float(previous.price)
        price_change_pct = (price_change / float(previous.price)) * 100

        if abs(price_change_pct) < self.price_change_pct_threshold:
            return None

        from config.settings import settings
        detected_at = datetime.utcnow()

        event = self.event_model(
            product_id=product.id,
            category_id=category_id,
            event_type="PRICE_CHANGE",
            severity='medium' if abs(price_change_pct) >= 30 else 'low',
            prev_price=previous.price,
            curr_price=current.price,
            price_change_pct=price_change_pct,
            detected_at=detected_at,
            time_window_start=detected_at - timedelta(days=settings.EVENT_LOOKBACK_DAYS),
            time_window_end=detected_at + timedelta(days=settings.EVENT_LOOKFORWARD_DAYS),
            context_collected=False,
            insight_generated=False
        )

        logger.info(
            f"가격 변동 감지: {product.product_name[:30]}... "
            f"(${previous.price} → ${current.price}, {price_change_pct:+.1f}%)"
        )

        return event

    def _check_review_surge(
        self,
        product: Any,
        category_id: int,
        current: Any,
        previous: Any
    ) -> Optional[RankingEvent]:
        """리뷰 급증 체크 (기존 로직 유지)"""

        if not current.review_count or not previous.review_count:
            return None

        review_change = current.review_count - previous.review_count

        if review_change < self.review_surge_threshold:
            return None

        from config.settings import settings
        detected_at = datetime.utcnow()

        event = self.event_model(
            product_id=product.id,
            category_id=category_id,
            event_type="REVIEW_SURGE",
            severity='high' if review_change >= 500 else 'medium',
            prev_review_count=previous.review_count,
            curr_review_count=current.review_count,
            review_change=review_change,
            detected_at=detected_at,
            time_window_start=detected_at - timedelta(days=settings.EVENT_LOOKBACK_DAYS),
            time_window_end=detected_at + timedelta(days=settings.EVENT_LOOKFORWARD_DAYS),
            context_collected=False,
            insight_generated=False
        )

        logger.info(
            f"리뷰 급증 감지: {product.product_name[:30]}... "
            f"({previous.review_count} → {current.review_count}, +{review_change})"
        )

        return event

    def _check_stock_change(
        self,
        product: Any,
        category_id: int,
        current: Any,
        previous: Any
    ) -> Optional[RankingEvent]:
        """재고 상태 변화 체크 (기존 로직 유지)"""

        if not current.stock_status or not previous.stock_status:
            return None

        if current.stock_status == previous.stock_status:
            return None

        # 품절 → 재입고 or 재입고 → 품절
        if 'out_of_stock' in [current.stock_status, previous.stock_status]:
            from config.settings import settings
            detected_at = datetime.utcnow()

            event = self.event_model(
                product_id=product.id,
                category_id=category_id,
                event_type="STOCK_CHANGE",
                severity='high' if current.stock_status == 'out_of_stock' else 'medium',
                detected_at=detected_at,
                time_window_start=detected_at - timedelta(days=settings.EVENT_LOOKBACK_DAYS),
                time_window_end=detected_at + timedelta(days=settings.EVENT_LOOKFORWARD_DAYS),
                context_collected=False,
                insight_generated=False
            )

            logger.info(
                f"재고 변화 감지: {product.product_name[:30]}... "
                f"({previous.stock_status} → {current.stock_status})"
            )

            return event

        return None
