"""
프롬프트 테스트 UI (Streamlit)
팀원들이 다양한 프롬프트를 테스트하고 비교할 수 있는 웹 인터페이스
"""
import sys
import random
import os
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, desc, and_, delete

from src.core.database import get_db_context, engine, Base
from src.models import (
    RankingEvent, AmazonProduct, AmazonCategory,
    EventContextSocial, EventInsight, AmazonRanking, Brand,
    ScenarioProduct, ScenarioCategory, ScenarioRanking, ScenarioRankingEvent
)
from src.services.insight_generator_openai import OpenAIInsightGenerator
from src.analyzers.event_detector import EventDetector
from config.settings import settings

# 페이지 설정
st.set_page_config(
    page_title="Laneige Prompt Tester",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)


def load_events() -> List[Dict[str, Any]]:
    """이벤트 목록 로드"""
    with get_db_context() as db:
        events = db.execute(
            select(RankingEvent)
            .order_by(desc(RankingEvent.detected_at))
            .limit(100)
        ).scalars().all()

        event_list = []
        for event in events:
            product = db.execute(
                select(AmazonProduct).where(AmazonProduct.id == event.product_id)
            ).scalar_one_or_none()

            category = db.execute(
                select(AmazonCategory).where(AmazonCategory.id == event.category_id)
            ).scalar_one_or_none()

            event_list.append({
                'id': event.id,
                'product_name': product.product_name if product else 'Unknown',
                'asin': product.asin if product else 'N/A',
                'category_name': category.category_name if category else 'Unknown',
                'event_type': event.event_type,
                'severity': event.severity,
                'prev_rank': event.prev_rank,
                'curr_rank': event.curr_rank,
                'rank_change': event.rank_change,
                'detected_at': event.detected_at,
                'event_obj': event  # 원본 객체
            })

        return event_list


def load_products(laneige_only: bool = True) -> List[Dict[str, Any]]:
    """제품 목록 로드"""
    with get_db_context() as db:
        query = select(AmazonProduct, Brand).join(
            Brand, AmazonProduct.brand_id == Brand.id, isouter=True
        )
        if laneige_only:
            query = query.where(Brand.brand_type == "target")

        products = db.execute(query).all()
        product_list = []
        for product, brand in products:
            product_list.append({
                "id": product.id,
                "name": product.product_name,
                "asin": product.asin,
                "brand_id": product.brand_id,
                "brand_name": brand.name if brand else "Unknown"
            })
        return product_list


def load_categories() -> List[Dict[str, Any]]:
    """카테고리 목록 로드"""
    with get_db_context() as db:
        categories = db.execute(
            select(AmazonCategory).order_by(AmazonCategory.category_name)
        ).scalars().all()
        return [
            {"id": c.id, "name": c.category_name}
            for c in categories
        ]


def ensure_scenario_tables():
    """시나리오 테이블 생성 보장"""
    Base.metadata.create_all(bind=engine)


def load_scenario_products() -> List[Dict[str, Any]]:
    with get_db_context() as db:
        products = db.execute(select(ScenarioProduct)).scalars().all()
        return [
            {
                "id": p.id,
                "name": p.product_name,
                "asin": p.asin,
                "brand_id": p.brand_id,
                "brand_name": "Laneige" if p.brand_id == 1 else f"Brand {p.brand_id}"
            }
            for p in products
        ]


def load_scenario_categories() -> List[Dict[str, Any]]:
    with get_db_context() as db:
        categories = db.execute(select(ScenarioCategory).order_by(ScenarioCategory.category_name)).scalars().all()
        return [{"id": c.id, "name": c.category_name} for c in categories]


def get_latest_scenario_ranking(db, product_id: int, category_id: int) -> Optional[ScenarioRanking]:
    return db.execute(
        select(ScenarioRanking)
        .where(
            and_(
                ScenarioRanking.product_id == product_id,
                ScenarioRanking.category_id == category_id
            )
        )
        .order_by(desc(ScenarioRanking.collected_at))
        .limit(1)
    ).scalar_one_or_none()


def get_latest_ranking(db, product_id: int, category_id: int) -> Optional[AmazonRanking]:
    return db.execute(
        select(AmazonRanking)
        .where(
            and_(
                AmazonRanking.product_id == product_id,
                AmazonRanking.category_id == category_id
            )
        )
        .order_by(desc(AmazonRanking.collected_at))
        .limit(1)
    ).scalar_one_or_none()


def build_rank_series(start_rank: int, end_rank: int, points: int, pattern: str) -> List[int]:
    if points < 2:
        points = 2

    if start_rank == end_rank:
        return [start_rank] * points

    if pattern == "surge":
        total_steps = points - 1
        if total_steps == 1:
            return [start_rank, end_rank]
        primary_step = -1 if end_rank < start_rank else 1
        opposite_step = -primary_step
        opposite_steps = max(1, (total_steps + 3) // 4)
        ranks = [start_rank]
        for i in range(total_steps - 1):
            delta = opposite_step if i < opposite_steps else primary_step
            next_rank = ranks[-1] + delta
            if primary_step == -1:
                min_rank = max(1, end_rank + 1)
                if next_rank < min_rank:
                    next_rank = min_rank
            else:
                max_rank = max(1, end_rank - 1)
                if next_rank > max_rank:
                    next_rank = max_rank
            if next_rank < 1:
                next_rank = 1
            ranks.append(next_rank)
        if primary_step == -1 and ranks[-1] <= end_rank:
            ranks[-1] = max(1, end_rank + 1)
        elif primary_step == 1 and ranks[-1] >= end_rank:
            ranks[-1] = max(1, end_rank - 1)
        ranks.append(end_rank)
        return ranks
    if pattern == "drop":
        total_steps = points - 1
        if total_steps == 1:
            return [start_rank, end_rank]
        primary_step = -1 if end_rank < start_rank else 1
        opposite_step = -primary_step
        opposite_steps = max(1, (total_steps + 3) // 4)
        ranks = [start_rank]
        for i in range(total_steps - 1):
            delta = opposite_step if i < opposite_steps else primary_step
            next_rank = ranks[-1] + delta
            if primary_step == -1:
                min_rank = max(1, end_rank + 1)
                if next_rank < min_rank:
                    next_rank = min_rank
            else:
                max_rank = max(1, end_rank - 1)
                if next_rank > max_rank:
                    next_rank = max_rank
            if next_rank < 1:
                next_rank = 1
            ranks.append(next_rank)
        if primary_step == -1 and ranks[-1] <= end_rank:
            ranks[-1] = max(1, end_rank + 1)
        elif primary_step == 1 and ranks[-1] >= end_rank:
            ranks[-1] = max(1, end_rank - 1)
        ranks.append(end_rank)
        return ranks

    step = (end_rank - start_rank) / (points - 1)
    return [round(start_rank + step * i) for i in range(points)]


def get_event_context(event: RankingEvent) -> Dict[str, Any]:
    """이벤트 컨텍스트 수집"""
    with get_db_context() as db:
        # 소셜 미디어 컨텍스트
        social_contexts = db.execute(
            select(EventContextSocial)
            .where(EventContextSocial.event_id == event.id)
        ).scalars().all()

        social_text = ""
        if social_contexts:
            for ctx in social_contexts:
                social_text += f"- {ctx.platform.upper()}: "
                if ctx.is_viral:
                    social_text += f"🔥 VIRAL - "
                social_text += f"{ctx.content_title or 'Untitled'}\n"
                social_text += f"  Views: {ctx.view_count or 0:,}, "
                social_text += f"Likes: {ctx.like_count or 0:,}\n"
        else:
            social_text = "No social media data available"

        # 트렌드 정보 (단순 버전)
        trend_text = f"Ranking change: {event.prev_rank} → {event.curr_rank}"
        if event.rank_change:
            direction = "up" if event.rank_change < 0 else "down"
            trend_text += f" ({abs(event.rank_change)} positions {direction})"

        return {
            'social_context': social_text,
            'trend_info': trend_text
        }


def prepare_event_data(event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """이벤트 데이터를 프롬프트 포맷에 맞게 준비"""
    event_obj = event_dict['event_obj']

    # 기본 데이터
    data = {
        'product_name': event_dict['product_name'],
        'asin': event_dict['asin'],
        'category_name': event_dict['category_name'],
        'prev_rank': int(event_obj.prev_rank or 0),
        'curr_rank': int(event_obj.curr_rank or 0),
        'rank_change': int(event_obj.rank_change or 0),
        'event_type': event_obj.event_type,
        'severity': event_obj.severity,
        'detected_at': event_obj.detected_at.strftime('%Y-%m-%d %H:%M:%S'),
        'price_change_pct': float(event_obj.price_change_pct or 0.0),
        'current_price': float(event_obj.curr_price or 0.0),
        'review_count_change': 0,  # TODO: 추후 추가
        'rating': float(event_obj.curr_rating or 0.0),
        'confidence': 0.0,  # TODO: 추후 추가
    }

    # 퍼센트 계산
    if data['prev_rank'] > 0:
        data['rank_change_pct'] = ((data['curr_rank'] - data['prev_rank']) / data['prev_rank']) * 100
    else:
        data['rank_change_pct'] = 0.0

    # 일관성 (임시)
    data['consistency'] = 80  # TODO: 실제 계산 로직 추가

    # 컨텍스트 추가
    context = get_event_context(event_obj)
    data.update(context)

    return data


def load_scenario_events() -> List[Dict[str, Any]]:
    """시나리오 이벤트 목록 로드"""
    with get_db_context() as db:
        events = db.execute(
            select(ScenarioRankingEvent)
            .order_by(desc(ScenarioRankingEvent.detected_at))
            .limit(100)
        ).scalars().all()

        event_list = []
        for event in events:
            product = db.execute(
                select(ScenarioProduct).where(ScenarioProduct.id == event.product_id)
            ).scalar_one_or_none()
            category = db.execute(
                select(ScenarioCategory).where(ScenarioCategory.id == event.category_id)
            ).scalar_one_or_none()

            event_list.append({
                'id': event.id,
                'product_name': product.product_name if product else 'Unknown',
                'asin': product.asin if product else 'N/A',
                'category_name': category.category_name if category else 'Unknown',
                'prev_rank': event.prev_rank or 0,
                'curr_rank': event.curr_rank or 0,
                'rank_change': event.rank_change or 0,
                'severity': event.severity,
                'event_type': event.event_type,
                'detected_at': event.detected_at,
                'price_change_pct': float(event.price_change_pct or 0.0),
                'current_price': float(event.curr_price or 0.0),
                'review_change': event.review_change or 0,
            })

        return event_list


def build_dummy_social_items(
    event_id: int,
    product_name: str,
    event_type: str,
    youtube_count: int,
    tiktok_count: int,
    instagram_count: int
) -> List[Dict[str, Any]]:
    rng = random.Random(event_id)

    titles = {
        "positive": [
            f"{product_name} review - why it's trending",
            f"{product_name} praise roundup",
            f"{product_name} top reasons people love it",
            f"{product_name} real-use review",
            f"{product_name} best features"
        ],
        "neutral": [
            f"{product_name} comparison review",
            f"{product_name} usage tips",
            f"{product_name} lineup breakdown",
            f"{product_name} Q&A recap",
            f"{product_name} balanced review"
        ],
        "negative": [
            f"{product_name} complaints explained",
            f"{product_name} what could be better",
            f"{product_name} critical review",
            f"{product_name} expectations vs reality",
            f"{product_name} improvement areas"
        ]
    }
    summaries = {
        "positive": [
            f"Positive buzz after {event_type}",
            "Strong mentions of feel/effect",
            "High value for price",
            "Rising repurchase intent",
            "Shared reasons for recommendation"
        ],
        "neutral": [
            "Balanced pros/cons recap",
            "Compared against alternatives",
            "Baseline usage feedback",
            "Feature-focused summary",
            "Value-oriented evaluation"
        ],
        "negative": [
            "Low perceived impact",
            "Price feels high for results",
            "Mixed results by skin type",
            "Scent/texture complaints",
            "Lower repurchase intent"
        ]
    }

    sentiment_weights = {
        "RANK_SURGE": {"positive": 0.6, "neutral": 0.3, "negative": 0.1},
        "RANK_DROP": {"positive": 0.1, "neutral": 0.3, "negative": 0.6},
        "STEADY_RISE": {"positive": 0.5, "neutral": 0.4, "negative": 0.1},
        "STEADY_DECLINE": {"positive": 0.1, "neutral": 0.4, "negative": 0.5},
    }
    weights = sentiment_weights.get(
        event_type,
        {"positive": 0.34, "neutral": 0.33, "negative": 0.33}
    )
    sentiment_keys = list(weights.keys())

    def make_items(platform: str, count: int) -> List[Dict[str, Any]]:
        items = []
        for i in range(count):
            sentiment = rng.choices(
                sentiment_keys,
                weights=[weights[k] for k in sentiment_keys],
                k=1
            )[0]
            items.append({
                "platform": platform,
                "title": rng.choice(titles[sentiment]),
                "summary": rng.choice(summaries[sentiment]),
                "views": rng.randint(1200, 280000),
                "likes": rng.randint(80, 12000),
                "comments": rng.randint(10, 1800),
                "sentiment": sentiment,
                "index": i + 1
            })
        return items

    items = []
    items.extend(make_items("youtube", youtube_count))
    items.extend(make_items("tiktok", tiktok_count))
    items.extend(make_items("instagram", instagram_count))
    return items


def format_dummy_social_context(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "No social media data available"

    lines = []
    for item in items:
        lines.append(
            f"- {item['platform'].upper()} #{item['index']}: {item['title']} | {item['summary']}\n"
            f"  Views: {item['views']:,}, Likes: {item['likes']:,}, Comments: {item['comments']:,}"
        )
    return "\n".join(lines)


def prepare_scenario_event_data(
    event_dict: Dict[str, Any],
    social_context: str
) -> Dict[str, Any]:
    data = {
        'product_name': event_dict['product_name'],
        'asin': event_dict['asin'],
        'category_name': event_dict['category_name'],
        'prev_rank': int(event_dict.get('prev_rank') or 0),
        'curr_rank': int(event_dict.get('curr_rank') or 0),
        'rank_change': int(event_dict.get('rank_change') or 0),
        'event_type': event_dict['event_type'],
        'severity': event_dict['severity'],
        'detected_at': event_dict['detected_at'].strftime('%Y-%m-%d %H:%M:%S'),
        'price_change_pct': float(event_dict.get('price_change_pct', 0.0)),
        'current_price': float(event_dict.get('current_price', 0.0)),
        'review_count_change': int(event_dict.get('review_change') or 0),
        'rating': 0.0,
        'confidence': 0.0,
        'social_context': social_context,
        'trend_info': f"Ranking change: {event_dict['prev_rank']} → {event_dict['curr_rank']}"
    }

    if data['prev_rank'] > 0:
        data['rank_change_pct'] = ((data['curr_rank'] - data['prev_rank']) / data['prev_rank']) * 100
    else:
        data['rank_change_pct'] = 0.0

    data['consistency'] = 80
    return data


def build_prompt_preview(generator: OpenAIInsightGenerator, template_key: str, event_data: Dict[str, Any]) -> Dict[str, str]:
    """선택된 템플릿의 시스템/유저 프롬프트 미리보기 생성"""
    if template_key not in generator.templates:
        return {"system": "N/A", "user": "N/A"}

    template = generator.templates[template_key]
    system_prompt = template.get("system_prompt", "")
    user_prompt = generator._format_user_prompt(template.get("user_prompt", ""), event_data)
    return {"system": system_prompt, "user": user_prompt}


def get_openai_model_choices() -> List[str]:
    """환경변수 기반 모델 목록 로드 (없으면 기본 목록 사용)"""
    env_models = os.environ.get("OPENAI_MODEL_CHOICES", "").strip()
    if env_models:
        return [m.strip() for m in env_models.split(",") if m.strip()]
    return [
        "gpt-5.2",
        "gpt-5.1",
        "gpt-5",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4o",
        "gpt-4o-mini",
    ]


def main():
    """메인 UI"""
    st.title("🧪 Laneige Prompt Tester")
    st.markdown("**프롬프트를 테스트하고 최적의 인사이트 생성 방식을 찾으세요**")

    # 사이드바 - 설정
    with st.sidebar:
        st.header("⚙️ 설정")

        api_key = settings.OPENAI_API_KEY or ""
        st.caption("OpenAI API 키는 `.env`의 `OPENAI_API_KEY`에서 읽어옵니다.")

        # 모델 선택
        model_options = get_openai_model_choices()
        default_model = settings.OPENAI_MODEL or "gpt-4.1"
        if default_model not in model_options:
            model_options = [default_model] + model_options
        model = st.selectbox(
            "모델",
            options=model_options,
            index=model_options.index(default_model),
            help="사용할 OpenAI 모델"
        )

        # 파라미터
        st.subheader("생성 파라미터")
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=0.3,
            step=0.1,
            help="높을수록 창의적, 낮을수록 일관적"
        )

        max_tokens = st.slider(
            "Max Tokens",
            min_value=500,
            max_value=4000,
            value=2000,
            step=100,
            help="생성할 최대 토큰 수"
        )

        st.markdown("---")
        st.markdown("### 💡 사용법")
        st.markdown("""
        1. 이벤트 선택
        2. 테스트할 프롬프트 선택
        3. 인사이트 생성
        4. 결과 비교 및 평가
        """)

    # API 키 확인
    if not api_key:
        st.warning("⚠️ OpenAI API 키가 설정되지 않았습니다.")
        st.info("`.env` 파일에 `OPENAI_API_KEY`를 설정하세요.")
        return

    try:
        generator = OpenAIInsightGenerator(api_key=api_key, model=model)
    except Exception as e:
        st.error(f"❌ OpenAI 초기화 실패: {e}")
        return

    # 템플릿 목록 (프롬프트 포함)
    templates = generator.templates

    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["📊 단일 테스트", "🔀 비교 테스트", "📈 결과 분석", "🧪 시나리오 테스트"])

    # === 탭 1: 단일 테스트 ===
    with tab1:
        st.header("단일 프롬프트 테스트")

        # 이벤트 로드
        events = load_events()

        if not events:
            st.warning("⚠️ 감지된 이벤트가 없습니다. 데이터를 수집한 후 다시 시도하세요.")
            st.code("python scripts/check_data.py")
        else:
            # 이벤트 선택
            col1, col2 = st.columns([2, 1])

            with col1:
                event_options = [
                    f"[{e['severity'].upper()}] {e['product_name'][:50]} | "
                    f"{e['prev_rank']}→{e['curr_rank']} | {e['detected_at'].strftime('%m/%d %H:%M')}"
                    for e in events
                ]

                selected_event_idx = st.selectbox(
                    "이벤트 선택",
                    range(len(events)),
                    format_func=lambda x: event_options[x]
                )

                selected_event = events[selected_event_idx]

            with col2:
                # 이벤트 상세 정보
                st.metric("Severity", selected_event['severity'].upper())
                st.metric("Rank Change", f"{selected_event['rank_change']:+d}")

            # 템플릿 선택
            st.subheader("프롬프트 템플릿 선택")

            template_cols = st.columns(3)
            template_items = list(templates.items())

            selected_template = None
            for i, (key, info) in enumerate(template_items):
                with template_cols[i % 3]:
                    if st.button(
                        f"**{info.get('name', key)}**\n\n{info.get('description', '')}",
                        key=f"template_{key}",
                        use_container_width=True
                    ):
                        selected_template = key

            # 템플릿이 선택되지 않았으면 기본값
            if selected_template is None and 'selected_template_single' not in st.session_state:
                st.session_state.selected_template_single = 'detailed'

            if selected_template:
                st.session_state.selected_template_single = selected_template

            current_template = st.session_state.get('selected_template_single', 'detailed')
            st.info(f"✅ 선택된 템플릿: **{templates[current_template].get('name', current_template)}**")

            # 프롬프트 미리보기 + 즉석 수정
            preview_event_data = prepare_event_data(selected_event)
            st.markdown("### 프롬프트 미리보기")
            single_system_key = f"single_system_override_{current_template}"
            single_user_key = f"single_user_override_{current_template}"
            if st.session_state.get("single_template_last") != current_template:
                st.session_state["single_template_last"] = current_template
                st.session_state[single_system_key] = templates[current_template].get("system_prompt", "")
                st.session_state[single_user_key] = templates[current_template].get("user_prompt", "")
            edited_system = st.text_area(
                "System Prompt",
                value=templates[current_template].get("system_prompt", ""),
                height=180,
                key=single_system_key
            )
            user_template_text = st.text_area(
                "User Prompt (템플릿)",
                value=templates[current_template].get("user_prompt", ""),
                height=240,
                key=single_user_key
            )
            prompt_preview = {
                "system": edited_system,
                "user": generator._format_user_prompt(user_template_text, preview_event_data)
            }
            st.caption("위 템플릿에 이벤트 데이터를 적용한 결과입니다.")
            st.code(prompt_preview["user"])

            # 생성 버튼
            if st.button("🚀 인사이트 생성", type="primary", use_container_width=True):
                with st.spinner("인사이트 생성 중..."):
                    try:
                        # 이벤트 데이터 준비
                        event_data = prepare_event_data(selected_event)

                        # 인사이트 생성
                        result = generator.generate_insight(
                            event_data=event_data,
                            template_key=current_template,
                            system_prompt_override=system_override,
                            user_prompt_override=prompt_preview["user"],
                            temperature=temperature,
                            max_tokens=max_tokens
                        )

                        # 결과 표시
                        st.success("✅ 인사이트 생성 완료")

                        # 메타데이터
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("모델", result['model'])
                        with col2:
                            st.metric("총 토큰", f"{result['tokens']['total']:,}")
                        with col3:
                            cost = generator.estimate_cost(
                                result['tokens']['prompt'],
                                result['tokens']['completion']
                            )
                            st.metric("예상 비용", f"${cost:.4f}")
                        with col4:
                            st.metric("생성 시간", f"{result['duration_seconds']:.2f}s")

                        # 인사이트 내용
                        st.markdown("### 📝 생성된 인사이트")
                        st.markdown(result['insight'])

                        # 세션 히스토리 저장
                        if st.button("📌 히스토리에 저장", use_container_width=True):
                            history = st.session_state.get("prompt_history", [])
                            history.append({
                                "mode": "single",
                                "event_id": selected_event["id"],
                                "event_name": selected_event["product_name"],
                                "template": result["template_name"],
                                "model": result["model"],
                                "tokens": result["tokens"]["total"],
                                "cost": generator.estimate_cost(
                                    result["tokens"]["prompt"],
                                    result["tokens"]["completion"]
                                ),
                                "generated_at": result["generated_at"],
                                "insight": result["insight"],
                            })
                            st.session_state["prompt_history"] = history
                            st.success("히스토리에 저장했습니다.")

                        # 평가 섹션
                        st.markdown("---")
                        st.markdown("### ⭐ 평가")
                        col1, col2 = st.columns(2)

                        with col1:
                            rating = st.slider(
                                "인사이트 품질 (1-5)",
                                min_value=1,
                                max_value=5,
                                value=3,
                                key=f"rating_{datetime.now().timestamp()}"
                            )

                        with col2:
                            usefulness = st.selectbox(
                                "유용성",
                                options=["매우 유용", "유용", "보통", "별로", "안 좋음"],
                                key=f"usefulness_{datetime.now().timestamp()}"
                            )

                        feedback = st.text_area(
                            "피드백 (선택)",
                            placeholder="이 프롬프트에 대한 의견을 남겨주세요...",
                            key=f"feedback_{datetime.now().timestamp()}"
                        )

                        if st.button("💾 평가 저장"):
                            st.success("평가가 저장되었습니다!")
                            # TODO: DB에 평가 저장

                    except Exception as e:
                        st.error(f"❌ 오류 발생: {e}")
                        import traceback
                        st.code(traceback.format_exc())

    # === 탭 2: 비교 테스트 ===
    with tab2:
        st.header("여러 프롬프트 비교")

        # 이벤트 선택
        events = load_events()
        if not events:
            st.warning("⚠️ 감지된 이벤트가 없습니다.")
        else:
            event_options = [
                f"[{e['severity'].upper()}] {e['product_name'][:50]} | "
                f"{e['prev_rank']}→{e['curr_rank']}"
                for e in events
            ]

            selected_event_idx_compare = st.selectbox(
                "비교할 이벤트 선택",
                range(len(events)),
                format_func=lambda x: event_options[x],
                key="compare_event"
            )

            # 템플릿 다중 선택
            st.subheader("비교할 템플릿 선택 (2-4개)")

            template_keys = list(templates.keys())
            selected_templates = st.multiselect(
                "템플릿",
                options=template_keys,
                default=template_keys[:2],
                format_func=lambda x: templates[x].get('name', x)
            )

            if len(selected_templates) < 2:
                st.warning("⚠️ 최소 2개의 템플릿을 선택하세요")
            elif len(selected_templates) > 4:
                st.warning("⚠️ 최대 4개까지 선택 가능합니다")
            else:
                compare_event_data = prepare_event_data(events[selected_event_idx_compare])
                compare_preview = build_prompt_preview(generator, selected_templates[0], compare_event_data)
                with st.expander("첫 번째 템플릿 프롬프트 미리보기", expanded=False):
                    st.markdown("**System Prompt**")
                    st.code(compare_preview["system"])
                    st.markdown("**User Prompt**")
                    st.code(compare_preview["user"])

                # 비교 생성 버튼
                if st.button("🔀 비교 인사이트 생성", type="primary", use_container_width=True):
                    with st.spinner(f"{len(selected_templates)}개의 인사이트 생성 중..."):
                        try:
                            # 이벤트 데이터 준비
                            event_data = prepare_event_data(events[selected_event_idx_compare])

                            # 여러 템플릿으로 생성
                            results = generator.generate_multiple_insights(
                                event_data=event_data,
                                template_keys=selected_templates,
                                temperature=temperature,
                                max_tokens=max_tokens
                            )

                            st.success(f"✅ {len(results)}개의 인사이트 생성 완료")

                            # 결과를 컬럼으로 표시
                            num_cols = min(len(results), 2)
                            cols = st.columns(num_cols)

                            for i, result in enumerate(results):
                                with cols[i % num_cols]:
                                    if 'error' in result:
                                        st.error(f"❌ {result['template_key']}: {result['error']}")
                                    else:
                                        st.markdown(f"### {result['template_name']}")

                                        # 메트릭
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.metric("토큰", f"{result['tokens']['total']:,}")
                                        with col2:
                                            cost = generator.estimate_cost(
                                                result['tokens']['prompt'],
                                                result['tokens']['completion']
                                            )
                                            st.metric("비용", f"${cost:.4f}")

                                        # 인사이트
                                        st.markdown(result['insight'])

                                        # 평가
                                        rating = st.slider(
                                            "품질",
                                            1, 5, 3,
                                            key=f"rating_compare_{i}"
                                        )

                                        st.markdown("---")

                            if st.button("📌 비교 결과 저장", use_container_width=True):
                                history = st.session_state.get("prompt_history", [])
                                for result in results:
                                    if 'error' in result:
                                        continue
                                    history.append({
                                        "mode": "compare",
                                        "event_id": events[selected_event_idx_compare]["id"],
                                        "event_name": events[selected_event_idx_compare]["product_name"],
                                        "template": result["template_name"],
                                        "model": result["model"],
                                        "tokens": result["tokens"]["total"],
                                        "cost": generator.estimate_cost(
                                            result["tokens"]["prompt"],
                                            result["tokens"]["completion"]
                                        ),
                                        "generated_at": result["generated_at"],
                                        "insight": result["insight"],
                                    })
                                st.session_state["prompt_history"] = history
                                st.success("비교 결과를 히스토리에 저장했습니다.")

                            # 총 비용
                            total_cost = sum([
                                generator.estimate_cost(r['tokens']['prompt'], r['tokens']['completion'])
                                for r in results if 'error' not in r
                            ])
                            st.info(f"💰 총 예상 비용: ${total_cost:.4f}")

                        except Exception as e:
                            st.error(f"❌ 오류 발생: {e}")
                            import traceback
                            st.code(traceback.format_exc())

    # === 탭 3: 결과 분석 ===
    with tab3:
        st.header("결과 분석")
        history = st.session_state.get("prompt_history", [])
        if not history:
            st.info("아직 저장된 히스토리가 없습니다. 단일/비교 테스트 후 저장하세요.")
        else:
            history_df = pd.DataFrame(history)
            st.dataframe(history_df, use_container_width=True)

            st.download_button(
                "⬇️ 히스토리 CSV 다운로드",
                data=history_df.to_csv(index=False).encode("utf-8"),
                file_name="prompt_history.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.subheader("요약")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 실행 수", len(history_df))
            with col2:
                st.metric("총 토큰", f"{history_df['tokens'].sum():,}")
            with col3:
                st.metric("총 비용(USD)", f"{history_df['cost'].sum():.4f}")

    # === 탭 4: 시나리오 테스트 ===
    @st.dialog("시나리오 테스트 도움말")
    def scenario_help_dialog():
        st.markdown(
            """
            **무엇을 하는 기능인가요?**
            - 실데이터 없이도 랭킹 변동 시나리오를 만들어 이벤트 감지/인사이트 흐름을 테스트합니다.

            **사용 순서**
            1. 더미 카테고리/제품 생성
            2. 제품/카테고리 선택
            3. 랭킹 시작/종료 값과 시간 범위 설정
            4. 시나리오 생성 및 이벤트 감지
            5. (선택) 임의 원인데이터 생성 후 인사이트 테스트

            **팁**
            - 변동폭이 작으면 이벤트가 감지되지 않을 수 있습니다.
            - 가격/리뷰 변화를 함께 주면 다른 이벤트 타입도 확인할 수 있습니다.

            **설정값 설명**
            - **카테고리/제품 생성 수**: 시나리오용 더미 카테고리/제품 개수입니다.
            - **시작 랭킹**: 시나리오 시작 시점의 랭킹입니다.
            - **종료 랭킹**: 시나리오 마지막 시점의 랭킹입니다.
            - **시간 범위(시간)**: 시나리오가 몇 시간에 걸쳐 진행됐는지입니다.
            - **가격 변화(%)**: 마지막 시점의 가격 변동률입니다.
            - **리뷰 증가량**: 마지막 시점의 리뷰 증가 수입니다.
            """
        )

    with tab4:
        st.header("시나리오 테스트")
        st.markdown("랭킹 데이터를 임의로 생성해 이벤트 감지/인사이트를 테스트합니다.")
        if st.button("❓ 도움말 보기"):
            scenario_help_dialog()

        ensure_scenario_tables()
        st.caption("시나리오용 더미 테이블을 사용합니다. 실데이터와 분리됩니다.")

        with st.expander("더미 데이터 생성", expanded=True):
            col_seed1, col_seed2 = st.columns(2)
            with col_seed1:
                seed_categories = st.number_input("카테고리 생성 수", min_value=1, max_value=20, value=3, step=1)
            with col_seed2:
                seed_products = st.number_input("제품 생성 수", min_value=1, max_value=50, value=5, step=1)

            col_seed3, col_seed4 = st.columns(2)
            with col_seed3:
                if st.button("🧩 더미 카테고리/제품 생성", use_container_width=True):
                    with get_db_context() as db:
                        existing_categories = db.execute(
                            select(ScenarioCategory).order_by(ScenarioCategory.id)
                        ).scalars().all()
                        existing_products = db.execute(
                            select(ScenarioProduct).order_by(ScenarioProduct.id)
                        ).scalars().all()

                        start_cat_index = len(existing_categories) + 1
                        start_prod_index = len(existing_products) + 1

                        for i in range(int(seed_categories)):
                            db.add(ScenarioCategory(category_name=f"Scenario Category {start_cat_index + i}"))

                        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                        for i in range(int(seed_products)):
                            db.add(ScenarioProduct(
                                asin=f"SCN-{timestamp}-{start_prod_index + i}",
                                product_name=f"LANEIGE Scenario Product {start_prod_index + i}",
                                brand_id=1
                            ))
                        db.commit()
                    st.success("✅ 더미 데이터가 생성되었습니다.")
            with col_seed4:
                if st.button("🧹 시나리오 데이터 초기화", use_container_width=True):
                    with get_db_context() as db:
                        db.execute(delete(ScenarioRankingEvent))
                        db.execute(delete(ScenarioRanking))
                        db.execute(delete(ScenarioProduct))
                        db.execute(delete(ScenarioCategory))
                        db.commit()
                    st.success("✅ 시나리오 데이터가 초기화되었습니다.")

        products = load_scenario_products()
        categories = load_scenario_categories()

        if not products:
            st.warning("⚠️ 시나리오 제품이 없습니다. 위에서 더미 데이터를 생성하세요.")
        if not categories:
            st.warning("⚠️ 시나리오 카테고리가 없습니다. 위에서 더미 데이터를 생성하세요.")
        if not products or not categories:
            st.stop()

        product_options = [
            f"[{p['brand_name']}] {p['name'][:60]} ({p['asin']})" for p in products
        ]
        selected_product_idx = st.selectbox(
            "제품 선택",
            range(len(products)),
            format_func=lambda x: product_options[x]
        )
        selected_product = products[selected_product_idx]

        category_options = [c["name"] for c in categories]
        selected_category_idx = st.selectbox(
            "카테고리 선택",
            range(len(categories)),
            format_func=lambda x: category_options[x]
        )
        selected_category = categories[selected_category_idx]

        col1, col2 = st.columns(2)
        with col1:
            start_rank = st.number_input("시작 랭킹", min_value=1, max_value=5000, value=80, step=1)
        with col2:
            end_rank = st.number_input("종료 랭킹", min_value=1, max_value=5000, value=25, step=1)

        col4, col5 = st.columns(2)
        with col4:
            hours_span = st.number_input("시간 범위(시간)", min_value=1, max_value=72, value=12, step=1)
        with col5:
            st.info(
                "생성 규칙\n- 1시간 간격으로 포인트 자동 생성\n- 시작~종료 랭킹을 선형으로 보간",
                icon="ℹ️"
            )

        st.subheader("감지 기준 (테스트용)")
        use_span_for_detection = st.checkbox(
            "분석 시간 범위를 시나리오 시간으로 맞춤",
            value=True
        )

        st.subheader("추가 변동")
        col6, col7 = st.columns(2)
        with col6:
            price_change_pct = st.slider("가격 변화 (%)", min_value=-50, max_value=50, value=0, step=5)
        with col7:
            review_surge = st.number_input("리뷰 증가량", min_value=0, max_value=2000, value=0, step=50)

        if st.button("🧪 시나리오 생성 및 이벤트 감지", type="primary", use_container_width=True):
            with st.spinner("시나리오 생성 중..."):
                try:
                    points = max(settings.EVENT_TREND_MIN_DATA_POINTS, int(hours_span) + 1)
                    pattern = "steady_rise" if end_rank < start_rank else "steady_decline"
                    ranks = build_rank_series(start_rank, end_rank, points, pattern)
                    now = datetime.utcnow()
                    step_minutes = int((hours_span * 60) / max(len(ranks) - 1, 1))

                    with get_db_context() as db:
                        # 이전 시나리오 데이터 제거 (동일 제품/카테고리)
                        db.execute(
                            delete(ScenarioRanking)
                            .where(
                                and_(
                                    ScenarioRanking.product_id == selected_product["id"],
                                    ScenarioRanking.category_id == selected_category["id"]
                                )
                            )
                        )

                        latest = get_latest_scenario_ranking(db, selected_product["id"], selected_category["id"])
                        base_price = float(latest.price) if latest and latest.price else 20.0
                        base_rating = float(latest.rating) if latest and latest.rating else 4.5
                        base_reviews = latest.review_count if latest and latest.review_count else 100
                        base_stock = latest.stock_status if latest and latest.stock_status else "in_stock"
                        base_prime = latest.is_prime if latest else False

                        for i, rank in enumerate(ranks):
                            timestamp = now - timedelta(minutes=step_minutes * (len(ranks) - 1 - i))
                            price = base_price
                            reviews = base_reviews
                            if i == len(ranks) - 1:
                                price = base_price * (1 + (price_change_pct / 100))
                                reviews = base_reviews + int(review_surge)

                            db.add(ScenarioRanking(
                                product_id=selected_product["id"],
                                category_id=selected_category["id"],
                                rank=int(rank),
                                price=price,
                                rating=base_rating,
                                review_count=reviews,
                                is_prime=base_prime,
                                stock_status=base_stock,
                                collected_at=timestamp,
                            ))

                        # 세션에 반영되도록 flush
                        db.flush()

                        detector = EventDetector(
                            trend_analysis_hours=int(hours_span) if use_span_for_detection else settings.EVENT_TREND_ANALYSIS_HOURS,
                            trend_min_data_points=settings.EVENT_TREND_MIN_DATA_POINTS,
                            trend_consistency_threshold=settings.EVENT_TREND_CONSISTENCY_THRESHOLD,
                            rank_thresholds=settings.EVENT_RANK_THRESHOLDS,
                            rank_change_pct_threshold=settings.EVENT_RANK_CHANGE_PCT_THRESHOLD,
                            use_hybrid_threshold=settings.EVENT_USE_HYBRID_THRESHOLD,
                            price_change_pct_threshold=settings.EVENT_PRICE_CHANGE_PCT_THRESHOLD,
                            review_surge_threshold=settings.EVENT_REVIEW_SURGE_THRESHOLD,
                            product_model=ScenarioProduct,
                            ranking_model=ScenarioRanking,
                            event_model=ScenarioRankingEvent,
                            target_brand_id=1,
                        )

                        events = detector.detect_events(db)
                        for event in events:
                            db.add(event)

                        filtered = [
                            e for e in events
                            if e.product_id == selected_product["id"]
                            and e.category_id == selected_category["id"]
                        ]
                        filtered_summaries = [
                            {
                                "event_type": e.event_type,
                                "prev_rank": e.prev_rank,
                                "curr_rank": e.curr_rank,
                                "rank_change": e.rank_change,
                                "severity": e.severity,
                            }
                            for e in filtered
                        ]

                        db.commit()

                    st.success(f"✅ 시나리오 데이터 {len(ranks)}건 생성 완료")
                    if filtered_summaries:
                        st.success(f"✅ 이벤트 감지: {len(filtered_summaries)}개")
                        for event in filtered_summaries:
                            st.markdown(
                                f"- **{event['event_type']}** | {event['prev_rank']}→{event['curr_rank']} "
                                f"({event['rank_change']:+d}) | {event['severity']}"
                            )
                    else:
                        st.warning("⚠️ 감지된 이벤트가 없습니다. 임계값/랭킹 변동을 조정해보세요.")
                        with get_db_context() as db:
                            cutoff_time = datetime.utcnow() - timedelta(
                                hours=int(hours_span) if use_span_for_detection else settings.EVENT_TREND_ANALYSIS_HOURS
                            )
                            debug_rankings = db.execute(
                                select(ScenarioRanking)
                                .where(
                                    and_(
                                        ScenarioRanking.product_id == selected_product["id"],
                                        ScenarioRanking.category_id == selected_category["id"],
                                        ScenarioRanking.collected_at >= cutoff_time
                                    )
                                )
                                .order_by(desc(ScenarioRanking.collected_at))
                            ).scalars().all()
                            trend_debug = detector._calculate_trend(debug_rankings)

                        if not debug_rankings:
                            st.info("감지 기간 내 랭킹 데이터가 없습니다.")
                        elif not trend_debug:
                            st.info("트렌드 계산에 필요한 유효 변동이 부족합니다.")
                        else:
                            abs_threshold = detector._get_rank_threshold(trend_debug["end_rank"])
                            change_pct = (
                                abs(trend_debug["total_change"]) / trend_debug["start_rank"] * 100
                                if trend_debug["start_rank"] else 0
                            )
                            st.markdown("**디버그 정보**")
                            st.code(
                                f"start_rank={trend_debug['start_rank']}, end_rank={trend_debug['end_rank']}, "
                                f"total_change={trend_debug['total_change']}, consistency={trend_debug['consistency']:.2f}, "
                                f"abs_threshold={abs_threshold}, change_pct={change_pct:.1f}%"
                            )

                except Exception as e:
                    st.error(f"❌ 시나리오 생성 실패: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        st.markdown("---")
        st.subheader("시나리오 인사이트 테스트")
        st.caption("이벤트 감지 → 임의 원인데이터 생성 → 인사이트 생성 순서로 실행됩니다.")

        scenario_events = load_scenario_events()
        if not scenario_events:
            st.info("감지된 시나리오 이벤트가 없습니다. 먼저 이벤트를 생성하세요.")
        else:
            event_options = [
                f"[{e['severity'].upper()}] {e['event_type']} | "
                f"{e['prev_rank']}→{e['curr_rank']} | {e['detected_at'].strftime('%m/%d %H:%M')}"
                for e in scenario_events
            ]
            selected_scenario_event_idx = st.selectbox(
                "시나리오 이벤트 선택",
                range(len(scenario_events)),
                format_func=lambda x: event_options[x],
                key="scenario_event_select"
            )
            selected_scenario_event = scenario_events[selected_scenario_event_idx]

            st.markdown("**1) 임의 원인데이터 생성**")
            col_ctx1, col_ctx2, col_ctx3 = st.columns(3)
            with col_ctx1:
                youtube_count = st.number_input("YouTube 개수", min_value=0, max_value=5, value=2, step=1)
            with col_ctx2:
                tiktok_count = st.number_input("TikTok 개수", min_value=0, max_value=5, value=2, step=1)
            with col_ctx3:
                instagram_count = st.number_input("Instagram 개수", min_value=0, max_value=5, value=2, step=1)

            context_store = st.session_state.setdefault("scenario_dummy_contexts", {})
            if st.button("📥 원인데이터 생성", use_container_width=True):
                items = build_dummy_social_items(
                    event_id=selected_scenario_event['id'],
                    product_name=selected_scenario_event['product_name'],
                    event_type=selected_scenario_event['event_type'],
                    youtube_count=int(youtube_count),
                    tiktok_count=int(tiktok_count),
                    instagram_count=int(instagram_count)
                )
                context_store[selected_scenario_event['id']] = items
                context_key = f"scenario_context_{selected_scenario_event['id']}"
                st.session_state[context_key] = format_dummy_social_context(items)
                st.success("임의 원인데이터를 생성했습니다.")

            context_items = context_store.get(selected_scenario_event['id'], [])
            context_text = format_dummy_social_context(context_items)
            context_key = f"scenario_context_{selected_scenario_event['id']}"
            if st.session_state.get("scenario_context_last") != selected_scenario_event['id']:
                st.session_state["scenario_context_last"] = selected_scenario_event['id']
                st.session_state[context_key] = context_text
            if context_key not in st.session_state:
                st.session_state[context_key] = context_text
            with st.expander("원인데이터 미리보기", expanded=bool(context_items)):
                edited_context_text = st.text_area(
                    "Social Context",
                    value=st.session_state.get(context_key, context_text),
                    height=180,
                    key=context_key
                )

            st.markdown("**2) 인사이트 생성**")
            if not templates:
                st.warning("프롬프트 템플릿을 찾을 수 없습니다. config/prompt_templates.yaml을 확인하세요.")
                selected_template_key = None
            else:
                template_keys = list(templates.keys())
                selected_template_key = st.selectbox(
                    "프롬프트 템플릿",
                    options=template_keys,
                    format_func=lambda key: templates[key].get('name', key),
                    key="scenario_template_select"
                )

            if selected_template_key:
                base_system = templates[selected_template_key].get("system_prompt", "")
                base_user = templates[selected_template_key].get("user_prompt", "")
            else:
                scenario_system_override = ""
                scenario_user_override = ""

            if selected_template_key:
                st.markdown("### 프롬프트 미리보기")
                scenario_system_key = f"scenario_system_override_{selected_template_key}"
                scenario_user_key = f"scenario_user_override_{selected_template_key}"
                if st.session_state.get("scenario_template_last") != selected_template_key:
                    st.session_state["scenario_template_last"] = selected_template_key
                    st.session_state[scenario_system_key] = base_system
                    st.session_state[scenario_user_key] = base_user
                if not st.session_state.get(scenario_system_key):
                    st.session_state[scenario_system_key] = base_system
                if not st.session_state.get(scenario_user_key):
                    st.session_state[scenario_user_key] = base_user
                scenario_system_override = st.text_area(
                    "System Prompt",
                    value=base_system,
                    height=180,
                    key=scenario_system_key
                )
                scenario_user_override = st.text_area(
                    "User Prompt (템플릿)",
                    value=base_user,
                    height=240,
                    key=scenario_user_key
                )

                preview_data = prepare_scenario_event_data(
                    selected_scenario_event,
                    st.session_state.get(context_key, edited_context_text)
                )
                prompt_preview = {
                    "system": scenario_system_override or base_system,
                    "user": generator._format_user_prompt(
                        scenario_user_override or base_user,
                        preview_data
                    )
                }
                st.caption("위 템플릿에 이벤트 데이터를 적용한 결과입니다.")
                st.text_area(
                    "Applied User Prompt",
                    value=prompt_preview["user"],
                    height=240,
                    disabled=True
                )

            if st.button("🧠 인사이트 생성", type="primary", use_container_width=True):
                if not context_items:
                    st.warning("원인데이터를 먼저 생성해주세요.")
                elif not selected_template_key:
                    st.warning("프롬프트 템플릿을 먼저 선택해주세요.")
                else:
                    with st.spinner("인사이트 생성 중..."):
                        try:
                            event_data = prepare_scenario_event_data(
                                selected_scenario_event,
                                st.session_state.get(context_key, edited_context_text)
                            )
                            result = generator.generate_insight(
                                event_data=event_data,
                                template_key=selected_template_key,
                                system_prompt_override=prompt_preview["system"],
                                user_prompt_override=prompt_preview["user"],
                                temperature=temperature,
                                max_tokens=max_tokens
                            )

                            st.success("✅ 인사이트 생성 완료")
                            col_a, col_b, col_c, col_d = st.columns(4)
                            with col_a:
                                st.metric("모델", result['model'])
                            with col_b:
                                st.metric("총 토큰", f"{result['tokens']['total']:,}")
                            with col_c:
                                cost = generator.estimate_cost(
                                    result['tokens']['prompt'],
                                    result['tokens']['completion']
                                )
                                st.metric("예상 비용", f"${cost:.4f}")
                            with col_d:
                                st.metric("생성 시간", f"{result['duration_seconds']:.2f}s")

                            st.markdown("### 📝 생성된 인사이트")
                            st.markdown(result['insight'])
                        except Exception as e:
                            st.error(f"❌ 인사이트 생성 실패: {e}")
                            import traceback
                            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
