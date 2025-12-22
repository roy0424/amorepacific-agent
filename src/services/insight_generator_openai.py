"""
OpenAI 인사이트 생성기
프롬프트 테스트 및 비교를 위한 OpenAI 기반 인사이트 생성
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from openai import OpenAI
import yaml
from pathlib import Path

from config.settings import settings


class OpenAIInsightGenerator:
    """OpenAI를 사용한 인사이트 생성"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Args:
            api_key: OpenAI API 키 (None이면 settings에서 가져옴)
            model: 사용할 모델 (gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-mini 등)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        """프롬프트 템플릿 로드"""
        template_path = Path(settings.BASE_DIR) / "config" / "prompt_templates.yaml"

        if not template_path.exists():
            logger.warning(f"템플릿 파일을 찾을 수 없습니다: {template_path}")
            return {}

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('templates', {})
        except Exception as e:
            logger.error(f"템플릿 로드 실패: {e}")
            return {}

    def get_available_templates(self) -> Dict[str, Dict[str, str]]:
        """사용 가능한 템플릿 목록 반환"""
        return {
            key: {
                'name': template.get('name', key),
                'description': template.get('description', '')
            }
            for key, template in self.templates.items()
        }

    def generate_insight(
        self,
        event_data: Dict[str, Any],
        template_key: str = "detailed",
        system_prompt_override: Optional[str] = None,
        user_prompt_override: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        이벤트 데이터를 기반으로 인사이트 생성

        Args:
            event_data: 이벤트 관련 데이터
            template_key: 사용할 템플릿 키
            temperature: 생성 온도 (0-2)
            max_tokens: 최대 토큰 수

        Returns:
            생성된 인사이트와 메타데이터
        """
        try:
            # 템플릿 가져오기
            if template_key not in self.templates:
                logger.error(f"템플릿을 찾을 수 없습니다: {template_key}")
                template_key = "basic"  # fallback

            template = self.templates[template_key]

            # 프롬프트 포맷팅
            system_prompt = system_prompt_override or template['system_prompt']
            if user_prompt_override is not None:
                user_prompt = user_prompt_override
            else:
                user_prompt = self._format_user_prompt(
                    template['user_prompt'],
                    event_data
                )

            # OpenAI API 호출
            start_time = datetime.now()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 결과 추출
            insight_text = response.choices[0].message.content
            usage = response.usage

            result = {
                'insight': insight_text,
                'template_key': template_key,
                'template_name': template.get('name', template_key),
                'model': self.model,
                'temperature': temperature,
                'tokens': {
                    'prompt': usage.prompt_tokens,
                    'completion': usage.completion_tokens,
                    'total': usage.total_tokens
                },
                'duration_seconds': duration,
                'generated_at': datetime.now(),
                'finish_reason': response.choices[0].finish_reason
            }

            logger.info(
                f"인사이트 생성 완료 (템플릿: {template_key}, "
                f"토큰: {usage.total_tokens}, 시간: {duration:.2f}s)"
            )

            return result

        except Exception as e:
            logger.error(f"인사이트 생성 실패: {e}")
            raise

    def generate_multiple_insights(
        self,
        event_data: Dict[str, Any],
        template_keys: List[str],
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> List[Dict[str, Any]]:
        """
        여러 템플릿으로 동시에 인사이트 생성

        Args:
            event_data: 이벤트 관련 데이터
            template_keys: 사용할 템플릿 키 리스트
            temperature: 생성 온도
            max_tokens: 최대 토큰 수

        Returns:
            생성된 인사이트 리스트
        """
        results = []

        for template_key in template_keys:
            try:
                result = self.generate_insight(
                    event_data=event_data,
                    template_key=template_key,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                results.append(result)
            except Exception as e:
                logger.error(f"템플릿 {template_key} 실패: {e}")
                results.append({
                    'template_key': template_key,
                    'error': str(e),
                    'generated_at': datetime.now()
                })

        return results

    def _format_user_prompt(
        self,
        template: str,
        event_data: Dict[str, Any]
    ) -> str:
        """
        프롬프트 템플릿에 이벤트 데이터 삽입

        Args:
            template: 프롬프트 템플릿
            event_data: 이벤트 데이터

        Returns:
            포맷팅된 프롬프트
        """
        # 기본값 설정
        defaults = {
            'product_name': 'N/A',
            'asin': 'N/A',
            'category_name': 'N/A',
            'prev_rank': 0,
            'curr_rank': 0,
            'rank_change': 0,
            'rank_change_pct': 0.0,
            'event_type': 'UNKNOWN',
            'severity': 'unknown',
            'detected_at': 'N/A',
            'consistency': 0,
            'price_change_pct': 0.0,
            'current_price': 0.0,
            'review_count_change': 0,
            'rating': 0.0,
            'confidence': 0.0,
            'social_context': 'No social media data available',
            'trend_info': 'No trend data available'
        }

        # 이벤트 데이터로 업데이트
        format_data = {**defaults, **event_data}

        try:
            return template.format(**format_data)
        except KeyError as e:
            logger.warning(f"프롬프트 포맷팅 중 누락된 키: {e}")
            # 누락된 키를 'N/A'로 채워서 재시도
            missing_keys = [key for key in str(e).split("'") if key]
            for key in missing_keys:
                if key not in format_data:
                    format_data[key] = 'N/A'
            return template.format(**format_data)

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        비용 추정 (USD)

        GPT-4o 가격 (2025년 기준):
        - Input: $2.50 per 1M tokens
        - Output: $10.00 per 1M tokens
        """
        if 'gpt-4o' in self.model:
            input_cost = (prompt_tokens / 1_000_000) * 2.50
            output_cost = (completion_tokens / 1_000_000) * 10.00
        elif 'gpt-4-turbo' in self.model:
            input_cost = (prompt_tokens / 1_000_000) * 10.00
            output_cost = (completion_tokens / 1_000_000) * 30.00
        elif 'gpt-3.5-turbo' in self.model:
            input_cost = (prompt_tokens / 1_000_000) * 0.50
            output_cost = (completion_tokens / 1_000_000) * 1.50
        else:
            # 알 수 없는 모델은 GPT-4o 기준
            input_cost = (prompt_tokens / 1_000_000) * 2.50
            output_cost = (completion_tokens / 1_000_000) * 10.00

        return input_cost + output_cost


def test_generator():
    """테스트 함수"""
    # 샘플 이벤트 데이터
    event_data = {
        'product_name': 'LANEIGE Lip Sleeping Mask Berry',
        'asin': 'B0XXXXXX',
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
        'social_context': '- TikTok: 3 viral videos (500K+ views)\n- YouTube: 2 review videos',
        'trend_info': 'Steady upward trend over last 12 hours: 15→12→9→7'
    }

    try:
        generator = OpenAIInsightGenerator(model="gpt-4o")

        print("\n=== Available Templates ===")
        templates = generator.get_available_templates()
        for key, info in templates.items():
            print(f"- {key}: {info['name']}")

        print("\n=== Testing 'basic' template ===")
        result = generator.generate_insight(event_data, template_key='basic')

        print(f"\nTemplate: {result['template_name']}")
        print(f"Model: {result['model']}")
        print(f"Tokens: {result['tokens']['total']}")
        print(f"Duration: {result['duration_seconds']:.2f}s")
        print(f"\nInsight:\n{result['insight']}")

        # 비용 계산
        cost = generator.estimate_cost(
            result['tokens']['prompt'],
            result['tokens']['completion']
        )
        print(f"\nEstimated Cost: ${cost:.6f}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_generator()
