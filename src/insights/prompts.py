"""
LLM 프롬프트 템플릿
인사이트 생성을 위한 프롬프트 관리
"""
from typing import Dict, List
import json


PROMPT_VERSION = "1.0"


def get_insight_system_prompt() -> str:
    """시스템 프롬프트 반환"""
    return """당신은 전문 이커머스 데이터 분석가입니다.
Amazon 랭킹 변동 이벤트를 분석하고, 그 원인을 파악하여 실행 가능한 인사이트를 제공합니다.

주요 역할:
1. 랭킹 변동의 주요 원인 파악 (소셜미디어, 리뷰, 가격, 경쟁사 등)
2. 유사한 과거 이벤트와 비교 분석
3. 비즈니스 임팩트 평가
4. 실행 가능한 권장 액션 제시

분석 시 고려사항:
- 데이터 기반의 객관적 분석
- 여러 요인의 복합적 영향 고려
- 상관관계와 인과관계 구분
- 실행 가능하고 구체적인 권장사항

응답은 반드시 다음 JSON 형식을 따라야 합니다:
{
  "summary": "1-2 문장으로 요약한 핵심 인사이트",
  "analysis": "상세한 분석 내용 (3-5 문단)",
  "likely_causes": [
    {"cause": "원인 설명", "confidence": 0.8, "evidence": "근거 데이터"}
  ],
  "recommendations": [
    {"action": "권장 액션", "priority": "high/medium/low", "rationale": "근거"}
  ],
  "confidence_score": 0.85
}
"""


def build_insight_user_prompt(
    event_data: Dict,
    context_data: Dict,
    similar_events: List[Dict]
) -> str:
    """
    사용자 프롬프트 생성

    Args:
        event_data: 이벤트 정보
        context_data: 컨텍스트 데이터 (소셜, 리뷰 등)
        similar_events: 유사 이벤트 목록

    Returns:
        완성된 사용자 프롬프트
    """
    prompt_parts = []

    # 1. 이벤트 개요
    prompt_parts.append("## 분석할 이벤트")
    prompt_parts.append(f"- 이벤트 타입: {event_data.get('event_type', 'N/A')}")
    prompt_parts.append(f"- 심각도: {event_data.get('severity', 'N/A')}")
    prompt_parts.append(f"- 제품: {event_data.get('product_name', 'N/A')}")
    prompt_parts.append(f"- 카테고리: {event_data.get('category_name', 'N/A')}")

    # 2. 랭킹 변동 정보
    if event_data.get('prev_rank') and event_data.get('curr_rank'):
        rank_change = event_data.get('rank_change', 0)
        direction = "상승" if rank_change < 0 else "하락"
        prompt_parts.append(f"\n### 랭킹 변동")
        prompt_parts.append(f"- 이전 순위: {event_data['prev_rank']}위")
        prompt_parts.append(f"- 현재 순위: {event_data['curr_rank']}위")
        prompt_parts.append(f"- 변동: {abs(rank_change)}위 {direction}")
        if event_data.get('rank_change_pct'):
            prompt_parts.append(f"- 변동률: {event_data['rank_change_pct']:.1f}%")

    # 3. 가격 변동
    if event_data.get('price_change_pct'):
        prompt_parts.append(f"\n### 가격 변동")
        prompt_parts.append(f"- 가격 변동률: {event_data['price_change_pct']:.1f}%")
        if event_data.get('prev_price') and event_data.get('curr_price'):
            prompt_parts.append(f"- 이전 가격: ${event_data['prev_price']}")
            prompt_parts.append(f"- 현재 가격: ${event_data['curr_price']}")

    # 4. 리뷰 변동
    if event_data.get('review_change'):
        prompt_parts.append(f"\n### 리뷰 변동")
        prompt_parts.append(f"- 리뷰 증가: {event_data['review_change']}개")
        if event_data.get('prev_review_count') and event_data.get('curr_review_count'):
            prompt_parts.append(f"- 이전: {event_data['prev_review_count']}개")
            prompt_parts.append(f"- 현재: {event_data['curr_review_count']}개")

    # 5. 소셜미디어 컨텍스트
    social_data = context_data.get('social_media', [])
    if social_data:
        prompt_parts.append(f"\n### 소셜미디어 활동 ({len(social_data)}개 컨텐츠)")

        # 플랫폼별 요약
        platform_summary = {}
        viral_count = 0
        for item in social_data:
            platform = item.get('platform', 'unknown')
            if platform not in platform_summary:
                platform_summary[platform] = {
                    'count': 0,
                    'total_engagement': 0,
                    'viral_count': 0
                }
            platform_summary[platform]['count'] += 1
            platform_summary[platform]['total_engagement'] += item.get('engagement_score', 0)
            if item.get('is_viral'):
                platform_summary[platform]['viral_count'] += 1
                viral_count += 1

        for platform, stats in platform_summary.items():
            avg_engagement = stats['total_engagement'] / stats['count'] if stats['count'] > 0 else 0
            prompt_parts.append(f"\n**{platform.upper()}**:")
            prompt_parts.append(f"- 컨텐츠 수: {stats['count']}개")
            prompt_parts.append(f"- 평균 참여도: {avg_engagement:,.0f}")
            prompt_parts.append(f"- 바이럴 컨텐츠: {stats['viral_count']}개")

        # 상위 바이럴 컨텐츠
        viral_contents = [item for item in social_data if item.get('is_viral')]
        if viral_contents:
            prompt_parts.append(f"\n**주요 바이럴 컨텐츠**:")
            for i, content in enumerate(viral_contents[:3], 1):
                prompt_parts.append(f"{i}. [{content.get('platform')}] {content.get('author', 'Unknown')}")
                prompt_parts.append(f"   - 조회수: {content.get('view_count', 0):,}")
                prompt_parts.append(f"   - 참여도: {content.get('engagement_score', 0):,}")
                if content.get('text'):
                    text_preview = content['text'][:100]
                    prompt_parts.append(f"   - 내용: {text_preview}...")

    # 6. 리뷰 컨텍스트 (향후 구현)
    review_data = context_data.get('reviews', [])
    if review_data:
        prompt_parts.append(f"\n### 리뷰 분석 ({len(review_data)}개)")
        # TODO: 리뷰 sentiment 분석 추가

    # 7. 경쟁사 컨텍스트 (향후 구현)
    competitor_data = context_data.get('competitors', [])
    if competitor_data:
        prompt_parts.append(f"\n### 경쟁사 동향 ({len(competitor_data)}개)")
        # TODO: 경쟁사 분석 추가

    # 8. 유사 이벤트 (RAG)
    if similar_events:
        prompt_parts.append(f"\n### 유사한 과거 이벤트 (참고용)")
        for i, similar in enumerate(similar_events[:3], 1):
            similarity = similar.get('similarity_score', 0)
            metadata = similar.get('metadata', {})
            prompt_parts.append(f"\n{i}. 이벤트 #{similar.get('event_id')} (유사도: {similarity:.2f})")
            prompt_parts.append(f"   - 타입: {metadata.get('event_type', 'N/A')}")
            prompt_parts.append(f"   - 심각도: {metadata.get('severity', 'N/A')}")
            if similar.get('document'):
                prompt_parts.append(f"   - 상황: {similar['document'][:150]}...")

    # 9. 분석 요청
    prompt_parts.append("\n\n## 분석 요청")
    prompt_parts.append("위 데이터를 종합적으로 분석하여:")
    prompt_parts.append("1. 랭킹 변동의 주요 원인을 파악하고")
    prompt_parts.append("2. 각 원인의 신뢰도를 평가하며")
    prompt_parts.append("3. 유사 이벤트와 비교하여")
    prompt_parts.append("4. 실행 가능한 권장 액션을 제시해주세요.")
    prompt_parts.append("\n응답은 반드시 JSON 형식으로 작성해주세요.")

    return "\n".join(prompt_parts)


def get_test_prompt() -> tuple:
    """테스트용 간단한 프롬프트 반환"""
    system = "You are a helpful assistant."
    user = "Say hello in Korean."
    return system, user
