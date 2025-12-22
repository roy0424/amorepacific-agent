"""
LLM Client - Claude API
인사이트 생성을 위한 Claude API 클라이언트
"""
import anthropic
from loguru import logger
from typing import Dict, List, Optional
import json

from config.settings import settings


class ClaudeClient:
    """Claude API 클라이언트"""

    def __init__(self):
        """Claude 클라이언트 초기화"""
        self.client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY
        )
        self.model = settings.ANTHROPIC_MODEL
        self.temperature = settings.ANTHROPIC_TEMPERATURE
        self.max_tokens = settings.ANTHROPIC_MAX_TOKENS

        logger.info(f"Claude 클라이언트 초기화 완료 - 모델: {self.model}")

    def generate_insight(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None
    ) -> Dict:
        """
        인사이트 생성

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트 (이벤트 데이터 포함)
            temperature: 온도 (기본값: settings.ANTHROPIC_TEMPERATURE)

        Returns:
            생성된 인사이트 (딕셔너리)
        """
        if temperature is None:
            temperature = self.temperature

        try:
            # Claude API 호출
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            # 응답 파싱
            content = response.content[0].text

            logger.info(f"Claude 인사이트 생성 완료 - 토큰: {response.usage.input_tokens} in, {response.usage.output_tokens} out")

            # JSON 파싱 시도
            try:
                insight_data = json.loads(content)
                return insight_data
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트 그대로 반환
                logger.warning("JSON 파싱 실패 - 텍스트 형식으로 반환")
                return {
                    "summary": content[:200],  # 첫 200자를 요약으로
                    "analysis": content,
                    "raw_response": content
                }

        except anthropic.APIError as e:
            logger.error(f"Claude API 오류: {e}")
            raise

    def generate_structured_insight(
        self,
        event_data: Dict,
        context_data: Dict,
        similar_events: List[Dict]
    ) -> Dict:
        """
        구조화된 인사이트 생성

        Args:
            event_data: 이벤트 정보
            context_data: 컨텍스트 데이터 (소셜미디어, 리뷰 등)
            similar_events: 유사 이벤트 목록

        Returns:
            구조화된 인사이트 딕셔너리
        """
        from src.insights.prompts import get_insight_system_prompt, build_insight_user_prompt

        # 프롬프트 생성
        system_prompt = get_insight_system_prompt()
        user_prompt = build_insight_user_prompt(event_data, context_data, similar_events)

        # 인사이트 생성
        return self.generate_insight(system_prompt, user_prompt)

    def test_connection(self) -> bool:
        """
        API 연결 테스트

        Returns:
            연결 성공 여부
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": "Hello"
                    }
                ]
            )
            logger.info("Claude API 연결 테스트 성공")
            return True
        except Exception as e:
            logger.error(f"Claude API 연결 테스트 실패: {e}")
            return False
