#!/usr/bin/env python3
"""
프롬프트 템플릿 테스트 스크립트
UI 없이 빠르게 템플릿을 테스트할 수 있습니다.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.insight_generator_openai import OpenAIInsightGenerator
from config.settings import settings

# 샘플 이벤트 데이터
SAMPLE_EVENT = {
    'product_name': 'LANEIGE Lip Sleeping Mask Berry',
    'asin': 'B074V96MPV',
    'category_name': 'Lip Care',
    'prev_rank': 15,
    'curr_rank': 7,
    'rank_change': -8,
    'rank_change_pct': -53.3,
    'event_type': 'STEADY_RISE',
    'severity': 'high',
    'detected_at': '2025-12-20 15:30:00',
    'consistency': 100,
    'price_change_pct': -5.0,
    'current_price': 18.99,
    'review_count_change': 150,
    'rating': 4.7,
    'confidence': 0.85,
    'social_context': (
        "- TIKTOK: 🔥 VIRAL - Laneige Lip Mask Glow Up Challenge\n"
        "  Views: 2,500,000, Likes: 350,000\n"
        "- YOUTUBE: Skincare Routine 2025 with Laneige\n"
        "  Views: 45,000, Likes: 3,200\n"
        "- TIKTOK: My Holy Grail Lip Products\n"
        "  Views: 180,000, Likes: 15,000"
    ),
    'trend_info': 'Steady upward trend over last 12 hours: 15 → 12 → 9 → 7 (consistent rise)'
}


def main():
    """메인 실행"""
    print("=" * 80)
    print("  🧪 프롬프트 템플릿 테스트")
    print("=" * 80)
    print()

    # API 키 확인
    if not settings.OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        print()
        print("설정 방법:")
        print("  1. .env 파일에 OPENAI_API_KEY=sk-... 추가")
        print("  2. 또는 환경변수로 설정")
        print()
        return

    try:
        # 생성기 초기화
        print("⏳ OpenAI 생성기 초기화 중...")
        generator = OpenAIInsightGenerator(model="gpt-4o")
        print("✅ 초기화 완료")
        print()

        # 사용 가능한 템플릿 목록
        templates = generator.get_available_templates()
        print(f"📋 사용 가능한 템플릿: {len(templates)}개")
        print()

        for key, info in templates.items():
            print(f"  • {key}: {info['name']}")
        print()

        # 사용자 입력
        print("테스트할 템플릿을 선택하세요:")
        print("  - 템플릿 키 입력 (예: basic, detailed)")
        print("  - 'all'을 입력하면 모든 템플릿 테스트")
        print("  - Enter를 누르면 'basic' 템플릿 사용")
        print()

        choice = input("선택: ").strip().lower()

        if not choice:
            choice = 'basic'

        if choice == 'all':
            # 모든 템플릿 테스트
            print()
            print("=" * 80)
            print("  모든 템플릿으로 인사이트 생성 중...")
            print("=" * 80)
            print()

            template_keys = list(templates.keys())
            results = generator.generate_multiple_insights(
                event_data=SAMPLE_EVENT,
                template_keys=template_keys,
                temperature=0.3,
                max_tokens=2000
            )

            total_cost = 0

            for i, result in enumerate(results, 1):
                print(f"\n{'=' * 80}")
                print(f"  [{i}/{len(results)}] {result['template_name']}")
                print("=" * 80)

                if 'error' in result:
                    print(f"❌ 오류: {result['error']}")
                    continue

                # 메타데이터
                print(f"\n모델: {result['model']}")
                print(f"토큰: {result['tokens']['total']:,} (입력: {result['tokens']['prompt']}, 출력: {result['tokens']['completion']})")
                print(f"시간: {result['duration_seconds']:.2f}초")

                cost = generator.estimate_cost(
                    result['tokens']['prompt'],
                    result['tokens']['completion']
                )
                total_cost += cost
                print(f"비용: ${cost:.4f}")

                # 인사이트
                print(f"\n인사이트:\n")
                print(result['insight'])
                print()

            print("=" * 80)
            print(f"  총 비용: ${total_cost:.4f}")
            print("=" * 80)

        else:
            # 단일 템플릿 테스트
            if choice not in templates:
                print(f"❌ '{choice}' 템플릿을 찾을 수 없습니다.")
                print(f"사용 가능한 템플릿: {', '.join(templates.keys())}")
                return

            print()
            print("=" * 80)
            print(f"  템플릿: {templates[choice]['name']}")
            print("=" * 80)
            print()
            print("⏳ 인사이트 생성 중...")

            result = generator.generate_insight(
                event_data=SAMPLE_EVENT,
                template_key=choice,
                temperature=0.3,
                max_tokens=2000
            )

            print("✅ 생성 완료")
            print()

            # 메타데이터
            print("=" * 80)
            print("  메타데이터")
            print("=" * 80)
            print(f"템플릿: {result['template_name']}")
            print(f"모델: {result['model']}")
            print(f"토큰: {result['tokens']['total']:,}")
            print(f"  - 입력: {result['tokens']['prompt']:,}")
            print(f"  - 출력: {result['tokens']['completion']:,}")
            print(f"시간: {result['duration_seconds']:.2f}초")

            cost = generator.estimate_cost(
                result['tokens']['prompt'],
                result['tokens']['completion']
            )
            print(f"비용: ${cost:.4f}")
            print()

            # 인사이트
            print("=" * 80)
            print("  생성된 인사이트")
            print("=" * 80)
            print()
            print(result['insight'])
            print()
            print("=" * 80)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
