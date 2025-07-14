"""
Enhanced Vector Engine
고도화된 벡터 엔진 - 메타데이터와 벡터 DB 통합
"""

import logging
import json
from typing import List, Dict, Optional, Union, Any
from pathlib import Path
from datetime import datetime
import numpy as np

from core.metadata_extractor import MetadataExtractor
from embeddings.text_embedder import PowerMarketEmbedder
from data.vectors.vector_store import VectorDatabase

logger = logging.getLogger(__name__)


class EnhancedVectorEngine:
    """
    고도화된 벡터 엔진
    - 메타데이터 추출과 벡터 저장을 통합
    - 전력시장 특화 검색 최적화
    - AI 활용을 위한 구조화된 정보 제공
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 구성 요소 초기화
        self.metadata_extractor = MetadataExtractor()
        self.embedder = PowerMarketEmbedder(
            model_name=config.get("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        )
        self.vector_db = VectorDatabase(
            db_path=config.get("VECTOR_DB_PATH", "./vector_db"),
            collection_name=config.get("COLLECTION_NAME", "power_market_docs")
        )
        
        # 메타데이터 스키마 정의
        self.metadata_schema = self._define_metadata_schema()
        
        logger.info("Enhanced Vector Engine 초기화 완료")
    
    def _define_metadata_schema(self) -> Dict[str, Any]:
        """메타데이터 스키마 정의"""
        return {
            # 기본 문서 정보
            "document_id": str,
            "chunk_id": str,
            "source_file": str,
            "file_type": str,
            "chunk_index": int,
            "total_chunks": int,
            
            # 전력시장 특화 메타데이터
            "market_domain": str,  # 발전계획, 계통운영, 전력거래, 시장운영
            "regulation_type": str,  # 규칙, 고시, 절차, 기술기준
            "importance_level": str,  # critical, important, informational
            "compliance_category": str,  # 의무, 권고, 참고
            
            # 구조적 메타데이터
            "section_hierarchy": str,  # 1.2.3 형태의 계층
            "section_title": str,
            "has_tables": bool,
            "has_formulas": bool,
            "has_images": bool,
            
            # 내용 메타데이터
            "text_complexity": str,  # simple, moderate, complex
            "readability_score": float,
            "keyword_density": float,
            "technical_term_count": int,
            
            # AI 최적화 정보
            "searchability_score": float,
            "summarization_priority": float,
            "qa_potential": float,
            "cross_reference_count": int,
            
            # 품질 지표
            "metadata_completeness": float,
            "content_quality": float,
            "processing_timestamp": str
        }
    
    def process_document_with_metadata(self, processed_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        문서를 메타데이터와 함께 처리하여 벡터 DB에 저장할 준비
        
        Args:
            processed_doc: MultimodalProcessor에서 처리된 문서
            
        Returns:
            벡터 DB에 저장할 준비가 된 문서 청크들
        """
        logger.info(f"문서 처리 시작: {processed_doc.get('document_id', 'unknown')}")
        
        # 1. 메타데이터 추출
        metadata = self.metadata_extractor.extract_metadata(processed_doc)
        
        # 2. 문서를 청크로 분할 (이미 처리된 경우 스킵)
        chunks = processed_doc.get("chunks", [])
        if not chunks:
            chunks = self._create_chunks_from_processed_doc(processed_doc)
        
        # 3. 각 청크에 대해 풍부한 메타데이터 생성
        enhanced_chunks = []
        for i, chunk in enumerate(chunks):
            enhanced_chunk = self._enhance_chunk_metadata(
                chunk, metadata, i, len(chunks), processed_doc
            )
            enhanced_chunks.append(enhanced_chunk)
        
        # 4. 임베딩 생성
        embedded_chunks = self.embedder.encode_documents(enhanced_chunks)
        
        logger.info(f"문서 처리 완료: {len(embedded_chunks)}개 청크 생성")
        return embedded_chunks
    
    def _create_chunks_from_processed_doc(self, processed_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """처리된 문서에서 청크 생성"""
        chunks = []
        content = processed_doc.get("content", {})
        
        # 섹션 기반 청킹 (우선순위)
        sections = content.get("sections", [])
        if sections:
            for i, section in enumerate(sections):
                chunk = {
                    "text": section.get("content", ""),
                    "metadata": {
                        "section_title": section.get("title", ""),
                        "section_index": i,
                        "chunk_type": "section"
                    }
                }
                chunks.append(chunk)
        
        # 문단 기반 청킹 (섹션이 없는 경우)
        elif content.get("paragraphs"):
            paragraphs = content.get("paragraphs", [])
            for i, paragraph in enumerate(paragraphs):
                chunk = {
                    "text": paragraph.get("content", ""),
                    "metadata": {
                        "paragraph_index": i,
                        "chunk_type": "paragraph"
                    }
                }
                chunks.append(chunk)
        
        # 전체 문서 청킹 (최후 수단)
        else:
            document_text = content.get("document", "")
            if document_text:
                # 고정 크기로 청킹
                chunk_size = self.config.get("CHUNK_SIZE", 1000)
                overlap = self.config.get("CHUNK_OVERLAP", 200)
                
                for i in range(0, len(document_text), chunk_size - overlap):
                    chunk_text = document_text[i:i + chunk_size]
                    chunk = {
                        "text": chunk_text,
                        "metadata": {
                            "chunk_start": i,
                            "chunk_type": "fixed_size"
                        }
                    }
                    chunks.append(chunk)
        
        return chunks
    
    def _enhance_chunk_metadata(self, 
                               chunk: Dict[str, Any], 
                               doc_metadata: Dict[str, Any], 
                               chunk_index: int,
                               total_chunks: int,
                               processed_doc: Dict[str, Any]) -> Dict[str, Any]:
        """청크 메타데이터 강화"""
        
        enhanced_chunk = chunk.copy()
        chunk_text = chunk.get("text", "")
        
        # 기본 문서 정보
        enhanced_chunk.update({
            "document_id": processed_doc.get("document_id"),
            "chunk_id": f"{processed_doc.get('document_id')}_{chunk_index}",
            "source_file": processed_doc.get("file_path", ""),
            "file_type": processed_doc.get("file_type", ""),
            "chunk_index": chunk_index,
            "total_chunks": total_chunks
        })
        
        # 전력시장 도메인 분류
        enhanced_chunk["market_domain"] = self._classify_market_domain(chunk_text, doc_metadata)
        enhanced_chunk["regulation_type"] = self._classify_regulation_type(chunk_text, doc_metadata)
        enhanced_chunk["importance_level"] = self._assess_importance_level(chunk_text)
        enhanced_chunk["compliance_category"] = self._classify_compliance(chunk_text)
        
        # 구조적 정보
        chunk_metadata = chunk.get("metadata", {})
        enhanced_chunk["section_hierarchy"] = self._extract_section_hierarchy(chunk_metadata)
        enhanced_chunk["section_title"] = chunk_metadata.get("section_title", "")
        
        # 멀티모달 요소
        enhanced_chunk["has_tables"] = self._contains_tables(chunk_text)
        enhanced_chunk["has_formulas"] = self._contains_formulas(chunk_text)
        enhanced_chunk["has_images"] = self._contains_images(chunk_text)
        
        # 내용 특성
        enhanced_chunk["text_complexity"] = self._assess_text_complexity(chunk_text)
        enhanced_chunk["readability_score"] = self._calculate_readability(chunk_text)
        enhanced_chunk["keyword_density"] = self._calculate_keyword_density(chunk_text)
        enhanced_chunk["technical_term_count"] = self._count_technical_terms(chunk_text)
        
        # AI 최적화 점수
        enhanced_chunk["searchability_score"] = self._calculate_searchability_score(chunk_text)
        enhanced_chunk["summarization_priority"] = self._calculate_summarization_priority(chunk_text)
        enhanced_chunk["qa_potential"] = self._calculate_qa_potential(chunk_text)
        enhanced_chunk["cross_reference_count"] = self._count_cross_references(chunk_text)
        
        # 품질 지표
        enhanced_chunk["metadata_completeness"] = self._calculate_metadata_completeness(enhanced_chunk)
        enhanced_chunk["content_quality"] = self._assess_content_quality(chunk_text)
        enhanced_chunk["processing_timestamp"] = datetime.now().isoformat()
        
        return enhanced_chunk
    
    def _classify_market_domain(self, text: str, doc_metadata: Dict[str, Any]) -> str:
        """전력시장 도메인 분류"""
        domain_keywords = {
            "발전계획": ["발전계획", "발전기", "급전", "출력", "운영계획"],
            "계통운영": ["계통", "송전", "배전", "전압", "주파수", "안정성"],
            "전력거래": ["거래", "입찰", "가격", "시장", "정산", "요금"],
            "시장운영": ["시장운영", "운영자", "참가자", "절차", "규칙"],
            "예비력": ["예비력", "보조서비스", "주파수조정", "전압조정"],
            "송전제약": ["송전제약", "제약", "혼잡", "선로", "용량"]
        }
        
        scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            scores[domain] = score
        
        if scores:
            return max(scores, key=scores.get)
        return "기타"
    
    def _classify_regulation_type(self, text: str, doc_metadata: Dict[str, Any]) -> str:
        """규제 유형 분류"""
        if any(word in text for word in ["규칙", "규정", "기준"]):
            return "규칙"
        elif any(word in text for word in ["고시", "공고", "알림"]):
            return "고시"
        elif any(word in text for word in ["절차", "매뉴얼", "가이드"]):
            return "절차"
        elif any(word in text for word in ["기술기준", "규격", "표준"]):
            return "기술기준"
        return "기타"
    
    def _assess_importance_level(self, text: str) -> str:
        """중요도 평가"""
        critical_words = ["필수", "의무", "반드시", "금지", "제재"]
        important_words = ["중요", "주의", "권장", "권고"]
        
        if any(word in text for word in critical_words):
            return "critical"
        elif any(word in text for word in important_words):
            return "important"
        return "informational"
    
    def _classify_compliance(self, text: str) -> str:
        """준수 카테고리 분류"""
        if any(word in text for word in ["의무", "반드시", "하여야"]):
            return "의무"
        elif any(word in text for word in ["권장", "권고", "바람직"]):
            return "권고"
        return "참고"
    
    def _extract_section_hierarchy(self, chunk_metadata: Dict[str, Any]) -> str:
        """섹션 계층 추출"""
        section_title = chunk_metadata.get("section_title", "")
        if not section_title:
            return ""
        
        # 조항 번호 추출
        import re
        patterns = [
            r"제\s*(\d+)\s*조",
            r"(\d+)\.(\d+)\.(\d+)",
            r"(\d+)\.(\d+)",
            r"(\d+)\."
        ]
        
        for pattern in patterns:
            match = re.search(pattern, section_title)
            if match:
                return match.group()
        
        return ""
    
    def _contains_tables(self, text: str) -> bool:
        """표 포함 여부"""
        table_indicators = ["표", "Table", "┌", "├", "│", "┐", "┤", "└", "┘"]
        return any(indicator in text for indicator in table_indicators)
    
    def _contains_formulas(self, text: str) -> bool:
        """수식 포함 여부"""
        formula_indicators = ["=", "∑", "∫", "α", "β", "γ", "±", "×", "÷"]
        return any(indicator in text for indicator in formula_indicators)
    
    def _contains_images(self, text: str) -> bool:
        """이미지 포함 여부"""
        image_indicators = ["그림", "Figure", "Fig.", "도", "이미지", "[그림"]
        return any(indicator in text for indicator in image_indicators)
    
    def _assess_text_complexity(self, text: str) -> str:
        """텍스트 복잡도 평가"""
        import re
        sentences = re.split(r'[.!?]+', text)
        if not sentences:
            return "simple"
        
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        if avg_length > 25:
            return "complex"
        elif avg_length > 15:
            return "moderate"
        return "simple"
    
    def _calculate_readability(self, text: str) -> float:
        """가독성 점수 계산"""
        import re
        sentences = re.split(r'[.!?]+', text)
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        complex_words = len([w for w in words if len(w) > 6])
        complex_ratio = complex_words / len(words) if words else 0
        
        readability = avg_sentence_length * 0.5 + complex_ratio * 100
        return round(max(0, min(100, readability)), 2)
    
    def _calculate_keyword_density(self, text: str) -> float:
        """키워드 밀도 계산"""
        power_keywords = [
            "전력", "발전", "계통", "시장", "거래", "운영", "예비력", "가격", 
            "용량", "송전", "배전", "주파수", "전압", "안정성"
        ]
        
        words = text.split()
        if not words:
            return 0.0
        
        keyword_count = sum(1 for word in words if any(kw in word for kw in power_keywords))
        return round(keyword_count / len(words), 3)
    
    def _count_technical_terms(self, text: str) -> int:
        """기술 용어 개수"""
        import re
        # 약어, 단위, 기술용어 패턴
        patterns = [
            r'[A-Z]{2,}',  # 약어
            r'\d+[A-Za-z]+',  # 숫자+단위
            r'[가-힣]+\([A-Za-z]+\)',  # 한글(영문)
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text))
        
        return count
    
    def _calculate_searchability_score(self, text: str) -> float:
        """검색 가능성 점수"""
        # 키워드 밀도, 기술용어 수, 텍스트 길이를 종합
        keyword_density = self._calculate_keyword_density(text)
        tech_terms = self._count_technical_terms(text)
        text_length = len(text.split())
        
        # 정규화된 점수 계산
        length_score = min(1.0, text_length / 100)  # 100단어 기준
        tech_score = min(1.0, tech_terms / 10)  # 10개 기준
        
        return round((keyword_density + tech_score + length_score) / 3, 3)
    
    def _calculate_summarization_priority(self, text: str) -> float:
        """요약 우선순위 점수"""
        importance = self._assess_importance_level(text)
        
        # 중요도에 따른 기본 점수
        base_scores = {
            "critical": 0.9,
            "important": 0.6,
            "informational": 0.3
        }
        
        base_score = base_scores.get(importance, 0.3)
        
        # 정의문, 핵심 정보 포함 시 가산점
        if any(word in text for word in ["정의", "이란", "라고 함", "기본원칙"]):
            base_score += 0.1
        
        return round(min(1.0, base_score), 3)
    
    def _calculate_qa_potential(self, text: str) -> float:
        """Q&A 잠재력 점수"""
        qa_indicators = [
            "이란", "라고 함", "정의", "의미", "무엇", "어떻게", "언제", "어디서",
            "절차", "방법", "기준", "조건", "요건"
        ]
        
        indicator_count = sum(1 for indicator in qa_indicators if indicator in text)
        max_indicators = 5
        
        return round(min(1.0, indicator_count / max_indicators), 3)
    
    def _count_cross_references(self, text: str) -> int:
        """상호 참조 개수"""
        import re
        ref_patterns = [
            r"제\s*\d+\s*조",
            r"별표\s*\d+",
            r"부록\s*\w+",
            r"\w+\s*규칙"
        ]
        
        count = 0
        for pattern in ref_patterns:
            count += len(re.findall(pattern, text))
        
        return count
    
    def _calculate_metadata_completeness(self, chunk: Dict[str, Any]) -> float:
        """메타데이터 완성도 계산"""
        required_fields = [
            "document_id", "chunk_id", "source_file", "market_domain",
            "regulation_type", "importance_level", "text_complexity"
        ]
        
        present_fields = sum(1 for field in required_fields if chunk.get(field))
        return round(present_fields / len(required_fields), 3)
    
    def _assess_content_quality(self, text: str) -> float:
        """콘텐츠 품질 평가"""
        if not text or len(text.strip()) < 10:
            return 0.0
        
        # 길이, 구조, 완성도 평가
        length_score = min(1.0, len(text) / 500)  # 500자 기준
        
        # 문장 구조 평가
        import re
        sentences = re.split(r'[.!?]+', text)
        structure_score = min(1.0, len(sentences) / 3)  # 3문장 기준
        
        # 완성도 평가 (문장이 온전한지)
        completeness_score = 1.0 if text.strip().endswith(('.', '!', '?')) else 0.7
        
        return round((length_score + structure_score + completeness_score) / 3, 3)
    
    def store_enhanced_documents(self, enhanced_chunks: List[Dict[str, Any]]) -> bool:
        """강화된 문서들을 벡터 DB에 저장"""
        try:
            # 벡터 DB 형식으로 변환
            vector_ready_docs = []
            
            for chunk in enhanced_chunks:
                # ChromaDB에 저장할 수 있는 형태로 메타데이터 정리
                clean_metadata = {}
                for key, value in chunk.items():
                    if key not in ['embedding', 'text']:
                        # ChromaDB는 기본 타입만 지원
                        if isinstance(value, (str, int, float, bool)):
                            clean_metadata[key] = value
                        else:
                            clean_metadata[key] = str(value)
                
                vector_doc = {
                    'id': chunk.get('chunk_id'),
                    'text': chunk.get('text', ''),
                    'embedding': chunk.get('embedding'),
                    'file_name': chunk.get('source_file', '').split('/')[-1],
                    **clean_metadata
                }
                
                vector_ready_docs.append(vector_doc)
            
            # 벡터 DB에 저장
            success = self.vector_db.add_documents(vector_ready_docs)
            
            if success:
                logger.info(f"Enhanced 문서 {len(enhanced_chunks)}개 저장 완료")
            
            return success
            
        except Exception as e:
            logger.error(f"Enhanced 문서 저장 실패: {e}")
            return False
    
    def search_with_metadata_filters(self, 
                                   query: str,
                                   domain_filter: Optional[str] = None,
                                   importance_filter: Optional[str] = None,
                                   regulation_filter: Optional[str] = None,
                                   top_k: int = 5) -> List[Dict[str, Any]]:
        """메타데이터 필터를 활용한 정밀 검색"""
        
        # 쿼리 임베딩 생성
        query_embedding = self.embedder.encode_text(query)
        
        # 메타데이터 필터 구성
        where_clause = {}
        if domain_filter:
            where_clause["market_domain"] = {"$eq": domain_filter}
        if importance_filter:
            where_clause["importance_level"] = {"$eq": importance_filter}
        if regulation_filter:
            where_clause["regulation_type"] = {"$eq": regulation_filter}
        
        # 검색 실행
        results = self.vector_db.search_similar(
            query_embedding=query_embedding,
            top_k=top_k,
            where=where_clause if where_clause else None
        )
        
        logger.info(f"메타데이터 필터 검색 완료: {len(results)}개 결과")
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """시스템 통계 정보"""
        stats = self.vector_db.get_collection_stats()
        metadata_stats = self.metadata_extractor.get_extraction_stats()
        
        return {
            "vector_db_stats": stats,
            "metadata_stats": metadata_stats,
            "embedding_model": self.embedder.model_name,
            "embedding_dimension": self.embedder.embedding_dimension,
            "timestamp": datetime.now().isoformat()
        }


def get_enhanced_vector_engine(config: Dict[str, Any]) -> EnhancedVectorEngine:
    """Enhanced Vector Engine 싱글톤 인스턴스 반환"""
    if not hasattr(get_enhanced_vector_engine, "_instance"):
        get_enhanced_vector_engine._instance = EnhancedVectorEngine(config)
    return get_enhanced_vector_engine._instance