"""
검색(Retrieval) 모듈
- 사용자 질문을 받아서 관련 문서를 찾는 역할
- 다양한 검색 전략 구현 (벡터 검색, 하이브리드 검색 등)
"""

import logging
from typing import List, Dict, Optional, Union
import numpy as np
import re
from dataclasses import dataclass

@dataclass
class SearchResult:
    """검색 결과를 담는 데이터 클래스"""
    id: str
    text: str
    metadata: Dict
    similarity: float
    source_file: str
    relevance_score: float = 0.0

class DocumentRetriever:
    """문서 검색 엔진 클래스"""
    
    def __init__(self, 
                 vector_db,
                 text_embedder,
                 top_k: int = 5,
                 similarity_threshold: float = 0.7):
        """
        Args:
            vector_db: 벡터 데이터베이스 인스턴스
            text_embedder: 텍스트 임베딩 인스턴스
            top_k: 반환할 최대 결과 수
            similarity_threshold: 유사도 임계값
        """
        self.logger = logging.getLogger(__name__)
        self.vector_db = vector_db
        self.text_embedder = text_embedder
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        # 전력시장 키워드 가중치
        self.power_market_keywords = {
            "발전계획": 1.5,
            "계통운영": 1.5,
            "전력거래": 1.4,
            "시장운영": 1.4,
            "예비력": 1.3,
            "송전제약": 1.3,
            "하루전": 1.2,
            "실시간": 1.2,
            "당일": 1.2,
            "급전": 1.2,
            "가격": 1.1,
            "입찰": 1.1,
            "발전량": 1.1,
            "수요": 1.1
        }
    
    def preprocess_query(self, query: str) -> str:
        """질문 전처리"""
        # 불필요한 문자 제거
        query = re.sub(r'[^\w\s가-힣]', ' ', query)
        
        # 연속된 공백 제거
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query
    
    def calculate_keyword_score(self, text: str, query: str) -> float:
        """키워드 기반 관련성 점수 계산"""
        score = 0.0
        text_lower = text.lower()
        query_lower = query.lower()
        
        # 질문의 키워드들
        query_words = query_lower.split()
        
        for word in query_words:
            if word in text_lower:
                # 전력시장 특화 키워드면 가중치 적용
                weight = self.power_market_keywords.get(word, 1.0)
                score += weight
        
        # 전체 단어 수로 정규화
        if len(query_words) > 0:
            score = score / len(query_words)
        
        return score
    
    def semantic_search(self, query: str, top_k: Optional[int] = None) -> List[SearchResult]:
        """의미적 검색 (임베딩 기반)"""
        try:
            if top_k is None:
                top_k = self.top_k
            
            # 질문을 벡터로 변환
            query_embedding = self.text_embedder.encode_text(query)
            
            # 벡터 데이터베이스에서 유사 문서 검색
            results = self.vector_db.search_similar(
                query_embedding=query_embedding,
                top_k=top_k * 2  # 더 많이 가져와서 후처리로 필터링
            )
            
            # 결과 변환 및 필터링
            search_results = []
            for result in results:
                if result['similarity'] >= self.similarity_threshold:
                    search_result = SearchResult(
                        id=result['id'],
                        text=result['text'],
                        metadata=result['metadata'],
                        similarity=result['similarity'],
                        source_file=result['metadata'].get('source_file', ''),
                        relevance_score=result['similarity']
                    )
                    search_results.append(search_result)
            
            # 상위 결과만 반환
            search_results = search_results[:top_k]
            
            self.logger.info(f"의미적 검색 완료: {len(search_results)}개 결과")
            return search_results
            
        except Exception as e:
            self.logger.error(f"의미적 검색 실패: {e}")
            return []
    
    def keyword_search(self, query: str, top_k: Optional[int] = None) -> List[SearchResult]:
        """키워드 검색 (텍스트 매칭 기반)"""
        try:
            if top_k is None:
                top_k = self.top_k
            
            # ChromaDB의 텍스트 검색 사용
            results = self.vector_db.search_by_text(
                query_text=query,
                top_k=top_k * 2
            )
            
            # 결과 변환 및 점수 계산
            search_results = []
            for result in results:
                keyword_score = self.calculate_keyword_score(result['text'], query)
                
                search_result = SearchResult(
                    id=result['id'],
                    text=result['text'],
                    metadata=result['metadata'],
                    similarity=result['similarity'],
                    source_file=result['metadata'].get('source_file', ''),
                    relevance_score=keyword_score
                )
                search_results.append(search_result)
            
            # 관련성 점수로 정렬
            search_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # 상위 결과만 반환
            search_results = search_results[:top_k]
            
            self.logger.info(f"키워드 검색 완료: {len(search_results)}개 결과")
            return search_results
            
        except Exception as e:
            self.logger.error(f"키워드 검색 실패: {e}")
            return []
    
    def hybrid_search(self, query: str, 
                     semantic_weight: float = 0.7,
                     keyword_weight: float = 0.3,
                     top_k: Optional[int] = None) -> List[SearchResult]:
        """하이브리드 검색 (의미적 + 키워드 검색 결합)"""
        try:
            if top_k is None:
                top_k = self.top_k
            
            # 각각의 검색 실행
            semantic_results = self.semantic_search(query, top_k * 2)
            keyword_results = self.keyword_search(query, top_k * 2)
            
            # 결과 통합 (ID 기준으로 중복 제거 및 점수 합산)
            combined_results = {}
            
            # 의미적 검색 결과 추가
            for result in semantic_results:
                combined_results[result.id] = result
                combined_results[result.id].relevance_score = (
                    result.similarity * semantic_weight
                )
            
            # 키워드 검색 결과 추가/갱신
            for result in keyword_results:
                if result.id in combined_results:
                    # 기존 결과에 키워드 점수 추가
                    combined_results[result.id].relevance_score += (
                        result.relevance_score * keyword_weight
                    )
                else:
                    # 새로운 결과 추가
                    result.relevance_score = result.relevance_score * keyword_weight
                    combined_results[result.id] = result
            
            # 최종 결과 리스트 생성 및 정렬
            final_results = list(combined_results.values())
            final_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # 상위 결과만 반환
            final_results = final_results[:top_k]
            
            self.logger.info(f"하이브리드 검색 완료: {len(final_results)}개 결과")
            return final_results
            
        except Exception as e:
            self.logger.error(f"하이브리드 검색 실패: {e}")
            return []
    
    def search_by_category(self, query: str, category: str, top_k: Optional[int] = None) -> List[SearchResult]:
        """카테고리별 검색"""
        try:
            if top_k is None:
                top_k = self.top_k
            
            # 카테고리 필터 생성
            where_filter = {"file_name": {"$contains": category}}
            
            # 질문을 벡터로 변환
            query_embedding = self.text_embedder.encode_text(query)
            
            # 필터링된 검색
            results = self.vector_db.search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                where=where_filter
            )
            
            # 결과 변환
            search_results = []
            for result in results:
                search_result = SearchResult(
                    id=result['id'],
                    text=result['text'],
                    metadata=result['metadata'],
                    similarity=result['similarity'],
                    source_file=result['metadata'].get('source_file', ''),
                    relevance_score=result['similarity']
                )
                search_results.append(search_result)
            
            self.logger.info(f"카테고리 '{category}' 검색 완료: {len(search_results)}개 결과")
            return search_results
            
        except Exception as e:
            self.logger.error(f"카테고리 검색 실패: {e}")
            return []
    
    def get_context_for_generation(self, search_results: List[SearchResult], 
                                 max_context_length: int = 4000) -> str:
        """검색 결과를 답변 생성용 컨텍스트로 변환"""
        try:
            context_parts = []
            current_length = 0
            
            for i, result in enumerate(search_results):
                # 소스 정보와 함께 텍스트 포맷팅
                formatted_text = f"""
[문서 {i+1}] (출처: {result.source_file}, 유사도: {result.similarity:.3f})
{result.text}
"""
                
                # 길이 확인
                if current_length + len(formatted_text) > max_context_length:
                    break
                
                context_parts.append(formatted_text)
                current_length += len(formatted_text)
            
            context = "\n".join(context_parts)
            
            self.logger.info(f"컨텍스트 생성 완료: {len(context_parts)}개 문서, {len(context)}자")
            return context
            
        except Exception as e:
            self.logger.error(f"컨텍스트 생성 실패: {e}")
            return ""

class PowerMarketRetriever(DocumentRetriever):
    """전력시장 특화 검색 엔진"""
    
    def __init__(self, vector_db, text_embedder, **kwargs):
        super().__init__(vector_db, text_embedder, **kwargs)
        
        # 전력시장 도메인별 가중치
        self.domain_weights = {
            "발전계획": 1.5,
            "계통운영": 1.4,
            "전력거래": 1.3,
            "시장운영": 1.3,
            "예비력": 1.2,
            "송전제약": 1.2
        }
    
    def smart_search(self, query: str, top_k: Optional[int] = None) -> List[SearchResult]:
        """전력시장 특화 스마트 검색"""
        # 질문에서 도메인 키워드 감지
        detected_domains = []
        query_lower = query.lower()
        
        for domain, weight in self.domain_weights.items():
            if domain in query_lower:
                detected_domains.append((domain, weight))
        
        if detected_domains:
            # 도메인이 감지되면 해당 도메인에 특화된 검색
            self.logger.info(f"감지된 도메인: {[d[0] for d in detected_domains]}")
            
            # 가장 높은 가중치의 도메인으로 카테고리 검색
            primary_domain = max(detected_domains, key=lambda x: x[1])[0]
            return self.search_by_category(query, primary_domain, top_k)
        else:
            # 일반적인 하이브리드 검색
            return self.hybrid_search(query, top_k=top_k)

if __name__ == "__main__":
    # 테스트 코드 (실제 데이터베이스와 임베딩 모델이 있을 때 실행)
    logging.basicConfig(level=logging.INFO)
    
    print("DocumentRetriever 모듈이 성공적으로 생성되었습니다.")
    print("실제 테스트를 위해서는 벡터 데이터베이스와 임베딩 모델이 필요합니다.")
