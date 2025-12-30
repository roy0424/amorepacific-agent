import openai
import yaml
import json
import os
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, List, Optional
from datetime import datetime

from src.insights.vector_store import EventVectorStore
from src.models.events import RankingEvent, EventContextSocial, EventInsight
from src.models.amazon import AmazonProduct, AmazonCategory
from config.settings import settings

class EventInsightGenerator:
    def __init__(self):
        """생성기 초기화 및 템플릿 로드"""
        self.vector_store = EventVectorStore()

        # 1. YAML 템플릿 로드
        try:
            with open("config/prompt_templates.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                self.templates = config['templates']
            logger.info(f"프롬프트 템플릿 로드 완료 ({len(self.templates)}개)")
        except Exception as e:
            logger.error(f"템플릿 파일 로드 실패: {e}")
            self.templates = {}

        # 2. OpenAI 클라이언트 초기화
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"  
        logger.info("EventInsightGenerator (OpenAI GPT-4o) 초기화 완료")

    def _get_competitor_analysis_from_file(self, file_path: str) -> str:
        """
        [RAG 구현부] 
        외부 경쟁사 텍스트 데이터를 읽어 현재 상황에 필요한 핵심 인사이트로 요약합니다.
        데이터가 확보되지 않았을 경우 샘플 파일을 참조할 수 있습니다.
        """
        if not os.path.exists(file_path):
            logger.warning(f"참조할 데이터 파일이 없습니다: {file_path}")
            return ""

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # RAG 요약 로직: 방대한 텍스트 중 핵심만 한 줄로 추출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 시장 분석가입니다. 제공된 데이터를 기반으로 경쟁사의 동향을 현재 우리 브랜드에 위협이 되는 요소 위주로 딱 한 줄로 요약하세요."},
                    {"role": "user", "content": f"다음 데이터에서 핵심 경쟁사 동향을 한 문장으로 추출해줘:\n\n{content}"}
                ],
                temperature=0 # 일관된 요약을 위해 0으로 설정
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"데이터 파일 분석 중 오류 발생: {e}")
            return ""

    def generate_insight(self, db: Session, event_id: int, competitor_text: str = "") -> Optional[EventInsight]:
        """특정 이벤트에 대한 인사이트 생성 (데이터 결합)"""
        logger.info(f"이벤트 {event_id} 인사이트 생성 시작")

        # 1. 이벤트 및 데이터 로드
        event = db.execute(select(RankingEvent).where(RankingEvent.id == event_id)).scalar_one_or_none()
        if not event: return None

        # 중복 생성 방지
        existing_insight = db.execute(select(EventInsight).where(EventInsight.event_id == event_id)).scalar_one_or_none()
        if existing_insight: return existing_insight

        event_data = self._prepare_event_data(db, event)
        context_data = self._collect_context_data(db, event)
        similar_events = self._find_similar_events(event_data)

        # 2. 템플릿 선정
        template_key = "detailed" if event.severity in ['critical', 'high'] or competitor_text else "basic"
        template = self.templates.get(template_key, self.templates.get('basic'))

        # 3. 컨텍스트 구성
        social_text = ""
        for s in context_data.get('social_media', []):
            viral_tag = "[🔥VIRAL]" if s['is_viral'] else ""
            social_text += f"- {viral_tag} {s['platform']} ({s['author']}): 조회 {s['view_count']}, 좋아요 {s['like_count']}\n"

        # 4. 프롬프트 완성 (RAG 결과물인 competitor_text 주입)
        user_prompt = template['user_prompt'].format(
            product_name=event_data['product_name'],
            category_name=event_data['category_name'],
            prev_rank=event_data['prev_rank'],
            curr_rank=event_data['curr_rank'],
            rank_change=event_data['rank_change'],
            event_type=event_data['event_type'],
            severity=event_data['severity'],
            price_change_pct=event_data['price_change_pct'] or 0,
            trend_info=f"경쟁사 동향: {competitor_text}" if competitor_text else "특이 경쟁 동향 없음",
            social_context=social_text or "해당 기간 소셜 지표 없음",
            review_count_change=event_data['review_change'] or 0
        )

        # 5. LLM 호출 및 저장
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": template['system_prompt']},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            llm_content = response.choices[0].message.content
            
            insight = EventInsight(
                event_id=event_id,
                summary=f"[{event_data['product_name']}] 분석 리포트",
                analysis=llm_content,
                likely_causes=json.dumps({"competitor": competitor_text, "social": social_text}, ensure_ascii=False),
                recommendations=json.dumps([], ensure_ascii=False),
                similar_events=json.dumps([e['event_id'] for e in similar_events], ensure_ascii=False),
                llm_model=self.model,
                generated_at=datetime.utcnow()
            )
            db.add(insight)
            event.insight_generated = True
            db.commit()
            return insight
        except Exception as e:
            logger.error(f"인사이트 생성 실패: {e}")
            return None

    def batch_generate_insights(self, db: Session, event_ids: Optional[List[int]] = None, limit: int = 10):
        """일괄 생성 시 외부 데이터를 참조하는 RAG 로직 수행"""
        if event_ids is None:
            events = db.execute(
                select(RankingEvent).where(RankingEvent.insight_generated == False).limit(limit)
            ).scalars().all()
            event_ids = [e.id for e in events]

        # [RAG 시작] 샘플 파일에서 경쟁사 인사이트 추출
        # 실제 운영시 이 경로에 경쟁사 데이터를 적재하면 됩니다.
        competitor_info = self._get_competitor_analysis_from_file("data/competitor_sample.txt")

        insights = []
        for event_id in event_ids:
            insight = self.generate_insight(db, event_id, competitor_text=competitor_info)
            if insight:
                insights.append(insight)
        return insights