"""
임베딩 모듈
- 텍스트를 벡터(숫자 배열)로 변환
- 한국어와 전력시장 전문용어를 잘 이해하는 모델 사용
"""

import logging
from typing import List, Dict, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

class TextEmbedder:
    """텍스트를 벡터로 변환하는 클래스"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Args:
            model_name: 사용할 임베딩 모델 이름
                      - paraphrase-multilingual-MiniLM-L12-v2: 다국어 지원, 경량화
                      - paraphrase-multilingual-mpnet-base-v2: 더 높은 성능, 무거움
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        
        try:
            self.logger.info(f"임베딩 모델 로딩 중: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
            self.logger.info(f"모델 로딩 완료. 임베딩 차원: {self.embedding_dimension}")
        except Exception as e:
            self.logger.error(f"모델 로딩 실패: {e}")
            raise
    
    def encode_text(self, text: str) -> np.ndarray:
        """단일 텍스트를 벡터로 변환"""
        try:
            # 텍스트가 비어있는지 확인
            if not text or not text.strip():
                self.logger.warning("빈 텍스트가 입력되었습니다")
                return np.zeros(self.embedding_dimension)
            
            # 임베딩 생성
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
            
        except Exception as e:
            self.logger.error(f"텍스트 임베딩 실패: {e}")
            return np.zeros(self.embedding_dimension)
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """여러 텍스트를 한번에 벡터로 변환 (더 효율적)"""
        try:
            if not texts:
                self.logger.warning("빈 텍스트 리스트가 입력되었습니다")
                return np.array([])
            
            # 빈 텍스트 필터링
            valid_texts = [text for text in texts if text and text.strip()]
            
            if not valid_texts:
                self.logger.warning("유효한 텍스트가 없습니다")
                return np.zeros((len(texts), self.embedding_dimension))
            
            self.logger.info(f"{len(valid_texts)}개 텍스트 배치 임베딩 시작")
            
            # 배치로 임베딩 생성
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=True
            )
            
            self.logger.info("배치 임베딩 완료")
            return embeddings
            
        except Exception as e:
            self.logger.error(f"배치 임베딩 실패: {e}")
            return np.zeros((len(texts), self.embedding_dimension))
    
    def encode_documents(self, documents: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """문서 조각들을 임베딩하고 메타데이터와 함께 반환"""
        try:
            if not documents:
                self.logger.warning("처리할 문서가 없습니다")
                return []
            
            # 텍스트만 추출
            texts = [doc.get('text', '') for doc in documents]
            
            # 배치 임베딩
            embeddings = self.encode_batch(texts)
            
            # 원본 문서에 임베딩 추가
            embedded_documents = []
            for i, doc in enumerate(documents):
                embedded_doc = doc.copy()
                embedded_doc['embedding'] = embeddings[i] if i < len(embeddings) else np.zeros(self.embedding_dimension)
                embedded_doc['embedding_model'] = self.model_name
                embedded_documents.append(embedded_doc)
            
            self.logger.info(f"{len(embedded_documents)}개 문서 임베딩 완료")
            return embedded_documents
            
        except Exception as e:
            self.logger.error(f"문서 임베딩 실패: {e}")
            return documents
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """두 임베딩 벡터 간의 코사인 유사도 계산"""
        try:
            # 벡터 정규화
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # 코사인 유사도 계산
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"유사도 계산 실패: {e}")
            return 0.0
    
    def find_most_similar(self, query_embedding: np.ndarray, 
                         document_embeddings: List[np.ndarray], 
                         top_k: int = 5) -> List[Dict[str, any]]:
        """쿼리와 가장 유사한 문서들을 찾기"""
        try:
            similarities = []
            
            for i, doc_embedding in enumerate(document_embeddings):
                similarity = self.calculate_similarity(query_embedding, doc_embedding)
                similarities.append({
                    'index': i,
                    'similarity': similarity
                })
            
            # 유사도 기준으로 정렬
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 상위 k개 반환
            return similarities[:top_k]
            
        except Exception as e:
            self.logger.error(f"유사 문서 찾기 실패: {e}")
            return []

class PowerMarketEmbedder(TextEmbedder):
    """전력시장 특화 임베딩 클래스"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        super().__init__(model_name)
        
        # 전력시장 전문용어 사전
        self.power_market_terms = {
            "발전계획": "power generation plan",
            "계통운영": "power system operation", 
            "전력거래": "electricity trading",
            "시장운영": "market operation",
            "예비력": "reserve power",
            "송전제약": "transmission constraint",
            "하루전시장": "day-ahead market",
            "실시간시장": "real-time market",
            "계통한계가격": "system marginal price",
            "급전지시": "dispatch instruction"
        }
    
    def preprocess_power_market_text(self, text: str) -> str:
        """전력시장 텍스트 전처리"""
        # 전문용어 정규화
        processed_text = text
        
        # 특수 문자 정리
        processed_text = processed_text.replace('\n', ' ').replace('\t', ' ')
        
        # 연속된 공백 제거
        import re
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()
        
        return processed_text
    
    def encode_text(self, text: str) -> np.ndarray:
        """전력시장 특화 텍스트 임베딩"""
        # 전처리 후 임베딩
        processed_text = self.preprocess_power_market_text(text)
        return super().encode_text(processed_text)

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # 일반 임베딩 테스트
    embedder = TextEmbedder()
    
    sample_texts = [
        "전력시장에서 발전계획 수립은 매우 중요합니다.",
        "계통운영자는 실시간으로 전력 수급을 관리합니다.",
        "예비력 확보를 통해 계통의 안정성을 유지합니다."
    ]
    
    # 단일 텍스트 임베딩
    single_embedding = embedder.encode_text(sample_texts[0])
    print(f"단일 임베딩 shape: {single_embedding.shape}")
    
    # 배치 임베딩
    batch_embeddings = embedder.encode_batch(sample_texts)
    print(f"배치 임베딩 shape: {batch_embeddings.shape}")
    
    # 유사도 계산
    similarity = embedder.calculate_similarity(batch_embeddings[0], batch_embeddings[1])
    print(f"텍스트 1과 2의 유사도: {similarity:.4f}")
    
    # 전력시장 특화 임베딩 테스트
    power_embedder = PowerMarketEmbedder()
    power_text = "하루전발전계획은 제16.4.1조에 의거하여 수립하며 전력거래일에 대해 최초로 통지되는 발전계획입니다."
    power_embedding = power_embedder.encode_text(power_text)
    print(f"전력시장 특화 임베딩 shape: {power_embedding.shape}")
