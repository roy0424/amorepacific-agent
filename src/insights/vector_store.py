"""
Vector Store for RAG - ChromaDB 기반
이벤트 임베딩 및 유사 이벤트 검색
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from loguru import logger
from typing import List, Dict, Optional
from pathlib import Path

from config.settings import settings


class EventVectorStore:
    """이벤트 벡터 스토어 - 유사 이벤트 검색을 위한 RAG"""

    def __init__(self, persist_directory: Optional[str] = None):
        """
        Args:
            persist_directory: ChromaDB 저장 경로 (기본: data/chromadb)
        """
        if persist_directory is None:
            persist_directory = str(settings.DATA_DIR / "chromadb")

        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Sentence Transformer 모델 로드 (임베딩용)
        # all-MiniLM-L6-v2: 빠르고 경량, 384차원 벡터
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # 컬렉션 가져오기 또는 생성
        try:
            self.collection = self.client.get_collection("ranking_events")
            logger.info(f"기존 컬렉션 로드: {self.collection.count()}개 이벤트")
        except:
            self.collection = self.client.create_collection(
                name="ranking_events",
                metadata={"hnsw:space": "cosine"}  # 코사인 유사도 사용
            )
            logger.info("새 컬렉션 생성: ranking_events")

    def _create_event_text(self, event_data: Dict) -> str:
        """
        이벤트 데이터를 텍스트로 변환 (임베딩용)

        Args:
            event_data: 이벤트 정보 딕셔너리

        Returns:
            임베딩할 텍스트 문자열
        """
        parts = [
            f"Event Type: {event_data.get('event_type', 'unknown')}",
            f"Severity: {event_data.get('severity', 'unknown')}",
        ]

        # 랭킹 변동 정보
        if event_data.get('rank_change'):
            parts.append(f"Rank Change: {event_data['rank_change']} positions")
        if event_data.get('rank_change_pct'):
            parts.append(f"Rank Change Percent: {event_data['rank_change_pct']:.1f}%")

        # 가격 변동 정보
        if event_data.get('price_change_pct'):
            parts.append(f"Price Change: {event_data['price_change_pct']:.1f}%")

        # 리뷰 변동 정보
        if event_data.get('review_change'):
            parts.append(f"Review Change: {event_data['review_change']} reviews")

        # 제품 정보
        if event_data.get('product_name'):
            parts.append(f"Product: {event_data['product_name']}")

        # 카테고리 정보
        if event_data.get('category_name'):
            parts.append(f"Category: {event_data['category_name']}")

        return ". ".join(parts)

    def add_event(self, event_id: int, event_data: Dict, metadata: Optional[Dict] = None):
        """
        이벤트를 벡터 DB에 추가

        Args:
            event_id: 이벤트 ID
            event_data: 이벤트 데이터 (event_type, severity, rank_change 등)
            metadata: 추가 메타데이터 (검색 필터링용)
        """
        # 텍스트 생성
        event_text = self._create_event_text(event_data)

        # 임베딩 생성
        embedding = self.embedding_model.encode(event_text).tolist()

        # 메타데이터 준비
        if metadata is None:
            metadata = {}

        metadata.update({
            'event_type': event_data.get('event_type', 'unknown'),
            'severity': event_data.get('severity', 'unknown'),
            'product_id': str(event_data.get('product_id', '')),
        })

        # ChromaDB에 추가
        self.collection.add(
            ids=[f"event_{event_id}"],
            embeddings=[embedding],
            documents=[event_text],
            metadatas=[metadata]
        )

        logger.debug(f"이벤트 {event_id} 벡터 DB에 추가 완료")

    def search_similar_events(
        self,
        event_data: Dict,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        유사한 이벤트 검색

        Args:
            event_data: 검색할 이벤트 데이터
            top_k: 반환할 유사 이벤트 개수
            filter_metadata: 메타데이터 필터 (예: {'event_type': 'RANK_SURGE'})

        Returns:
            유사 이벤트 목록 (id, distance, metadata 포함)
        """
        # 검색 쿼리 텍스트 생성
        query_text = self._create_event_text(event_data)

        # 쿼리 임베딩 생성
        query_embedding = self.embedding_model.encode(query_text).tolist()

        # ChromaDB 검색
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k + 1,  # 자기 자신 제외를 위해 +1
            where=filter_metadata
        )

        # 결과 파싱
        similar_events = []
        for i in range(len(results['ids'][0])):
            event_id_str = results['ids'][0][i]
            event_id = int(event_id_str.replace('event_', ''))
            distance = results['distances'][0][i]

            similar_events.append({
                'event_id': event_id,
                'similarity_score': 1 - distance,  # distance를 similarity로 변환
                'metadata': results['metadatas'][0][i],
                'document': results['documents'][0][i]
            })

        logger.info(f"유사 이벤트 {len(similar_events)}개 검색 완료")
        return similar_events

    def get_event_count(self) -> int:
        """벡터 DB에 저장된 이벤트 개수 반환"""
        return self.collection.count()

    def reset(self):
        """벡터 DB 초기화 (개발/테스트용)"""
        self.client.delete_collection("ranking_events")
        self.collection = self.client.create_collection(
            name="ranking_events",
            metadata={"hnsw:space": "cosine"}
        )
        logger.warning("벡터 DB 초기화됨")
