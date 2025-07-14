"""
Enhanced 전력시장 RAG 시스템 메인 모듈
- 고도화된 메타데이터와 벡터 엔진 활용
- 전력시장 특화 연관성 매핑
- AI가 최대한 활용할 수 있는 구조화된 정보 제공
"""

import logging
import os
import yaml
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

# 각 모듈 임포트
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Enhanced 모듈들
from core.enhanced_vector_engine import EnhancedVectorEngine
from core.multimodal_processor import MultimodalProcessor
from core.document_hierarchy_analyzer import DocumentHierarchyAnalyzer
from core.relationship_mapper import PowerMarketRelationshipMapper
from embeddings.text_embedder import PowerMarketEmbedder
from generation.answer_generator import PowerMarketAnswerGenerator


class EnhancedPowerMarketRAG:
    """
    Enhanced 전력시장 RAG 시스템
    - 고도화된 메타데이터 활용
    - 구조적 계층 정보 기반 검색
    - 연관성 매핑을 통한 맥락적 답변
    - AI 친화적 정보 구조화
    """
    
    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: 설정 파일 경로
        """
        self.logger = logging.getLogger(__name__)
        
        # 설정 로드
        self.config = self._load_config(config_path)
        
        # 구성 요소 초기화 플래그
        self.is_initialized = False
        
        # Enhanced 구성 요소들
        self.multimodal_processor = None
        self.enhanced_vector_engine = None
        self.hierarchy_analyzer = None
        self.relationship_mapper = None
        self.embedder = None
        self.answer_generator = None
        
        self.logger.info("Enhanced PowerMarketRAG 시스템이 생성되었습니다")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """설정 파일 로드"""
        if config_path is None:
            config_path = "config/config.yaml"
        
        default_config = {
            "VECTOR_DB_TYPE": "chromadb",
            "VECTOR_DB_PATH": "./vector_db",
            "COLLECTION_NAME": "power_market_docs_enhanced",
            "EMBEDDING_MODEL": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            "EMBEDDING_DIMENSION": 768,
            "CHUNK_SIZE": 1000,
            "CHUNK_OVERLAP": 200,
            "TOP_K": 5,
            "SIMILARITY_THRESHOLD": 0.7,
            "API_HOST": "0.0.0.0",
            "API_PORT": 8000,
            "LOG_LEVEL": "INFO"
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                default_config.update(file_config)
                self.logger.info(f"설정 파일 로드 완료: {config_path}")
            else:
                self.logger.warning(f"설정 파일이 없어 기본값 사용: {config_path}")
        except Exception as e:
            self.logger.error(f"설정 파일 로드 실패, 기본값 사용: {e}")
        
        return default_config
    
    def initialize(self) -> bool:
        """모든 구성 요소 초기화"""
        try:
            self.logger.info("Enhanced RAG 시스템 초기화 시작")
            
            # 1. Multimodal Processor
            self.logger.info("Multimodal Processor 초기화 중...")
            self.multimodal_processor = MultimodalProcessor()
            
            # 2. Enhanced Vector Engine
            self.logger.info("Enhanced Vector Engine 초기화 중...")
            self.enhanced_vector_engine = EnhancedVectorEngine(self.config)
            
            # 3. Document Hierarchy Analyzer
            self.logger.info("Document Hierarchy Analyzer 초기화 중...")
            self.hierarchy_analyzer = DocumentHierarchyAnalyzer()
            
            # 4. Power Market Embedder
            self.logger.info("임베딩 모델 초기화 중...")
            self.embedder = PowerMarketEmbedder(
                model_name=self.config["EMBEDDING_MODEL"]
            )
            
            # 5. Relationship Mapper
            self.logger.info("Relationship Mapper 초기화 중...")
            self.relationship_mapper = PowerMarketRelationshipMapper(self.embedder)
            
            # 6. Answer Generator
            self.logger.info("Answer Generator 초기화 중...")
            self.answer_generator = PowerMarketAnswerGenerator()
            
            self.is_initialized = True
            self.logger.info("Enhanced RAG 시스템 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"Enhanced RAG 시스템 초기화 실패: {e}")
            return False
    
    def ask_enhanced(self, 
                    question: str, 
                    search_method: str = "hybrid",
                    domain_filter: Optional[str] = None,
                    importance_filter: Optional[str] = None,
                    include_relationships: bool = True) -> Dict[str, Any]:
        """
        Enhanced 질문 답변 생성
        
        Args:
            question: 질문
            search_method: 검색 방법 (semantic, keyword, hybrid, smart)
            domain_filter: 도메인 필터 (발전계획, 계통운영, 전력거래, 시장운영 등)
            importance_filter: 중요도 필터 (critical, important, informational)
            include_relationships: 관련 문서 연관성 포함 여부
            
        Returns:
            Enhanced 답변 결과
        """
        try:
            if not self.is_initialized:
                return {
                    "answer": "시스템이 초기화되지 않았습니다.",
                    "confidence": 0.0,
                    "sources": [],
                    "error": "System not initialized"
                }
            
            self.logger.info(f"Enhanced 질문 처리 시작: {question}")
            
            # 1. 메타데이터 필터를 활용한 정밀 검색
            search_results = self.enhanced_vector_engine.search_with_metadata_filters(
                query=question,
                domain_filter=domain_filter,
                importance_filter=importance_filter,
                top_k=self.config["TOP_K"]
            )
            
            if not search_results:
                return {
                    "answer": "관련 문서를 찾을 수 없습니다.",
                    "confidence": 0.0,
                    "sources": [],
                    "search_results": 0,
                    "filters_applied": {
                        "domain": domain_filter,
                        "importance": importance_filter
                    }
                }
            
            # 2. 연관 문서 찾기 (옵션)
            related_docs = []
            if include_relationships and search_results:
                primary_doc_id = search_results[0].get("id")
                if primary_doc_id:
                    related_docs = self.relationship_mapper.get_related_documents(
                        document_id=primary_doc_id,
                        max_results=3
                    )
            
            # 3. 컨텍스트 생성 (계층 정보 포함)
            enriched_context = self._create_enriched_context(search_results, related_docs)
            
            # 4. 답변 생성
            generation_result = self.answer_generator.generate_answer(
                context=enriched_context["text"],
                query=question,
                sources=enriched_context["sources"]
            )
            
            # 5. Enhanced 결과 구성
            result = {
                "answer": generation_result.answer,
                "confidence": generation_result.confidence,
                "sources": generation_result.sources,
                "reasoning": generation_result.reasoning,
                "metadata": generation_result.metadata,
                
                # Enhanced 정보
                "search_results": len(search_results),
                "related_documents": len(related_docs),
                "filters_applied": {
                    "domain": domain_filter,
                    "importance": importance_filter
                },
                "enriched_context": {
                    "hierarchical_info": enriched_context["hierarchical_info"],
                    "domain_distribution": enriched_context["domain_distribution"],
                    "importance_levels": enriched_context["importance_levels"]
                },
                "search_method": search_method
            }
            
            self.logger.info(f"Enhanced 질문 처리 완료 (신뢰도: {generation_result.confidence:.3f})")
            return result
            
        except Exception as e:
            self.logger.error(f"Enhanced 질문 처리 실패: {e}")
            return {
                "answer": "답변 생성 중 오류가 발생했습니다.",
                "confidence": 0.0,
                "sources": [],
                "error": str(e)
            }
    
    def _create_enriched_context(self, search_results: List[Dict], related_docs: List[Dict]) -> Dict[str, Any]:
        """풍부한 컨텍스트 생성"""
        
        # 기본 텍스트 컨텍스트
        context_parts = []
        sources = []
        hierarchical_info = []
        domain_distribution = {}
        importance_levels = {}
        
        # 주요 검색 결과 처리
        for i, result in enumerate(search_results):
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            
            # 계층 정보 추가
            hierarchy_path = metadata.get("full_path", "")
            hierarchy_title = metadata.get("hierarchy_title", "")
            
            if hierarchy_path or hierarchy_title:
                context_header = f"[{hierarchy_path or hierarchy_title}]"
                context_parts.append(f"{context_header}\n{text}")
                hierarchical_info.append({
                    "path": hierarchy_path,
                    "title": hierarchy_title,
                    "result_index": i
                })
            else:
                context_parts.append(text)
            
            # 메타데이터 통계
            domain = metadata.get("market_domain", "기타")
            importance = metadata.get("importance_level", "informational")
            
            domain_distribution[domain] = domain_distribution.get(domain, 0) + 1
            importance_levels[importance] = importance_levels.get(importance, 0) + 1
            
            # 소스 정보
            source_info = metadata.get("source_file", "")
            if source_info:
                sources.append(source_info)
        
        # 관련 문서 추가 (간략하게)
        if related_docs:
            context_parts.append("\n[관련 문서 정보]")
            for rel_doc in related_docs[:2]:  # 최대 2개만
                rel_info = rel_doc.get("relationship", {})
                context_parts.append(f"- {rel_info.get('description', '')}")
        
        return {
            "text": "\n\n".join(context_parts),
            "sources": list(set(sources)),
            "hierarchical_info": hierarchical_info,
            "domain_distribution": domain_distribution,
            "importance_levels": importance_levels
        }
    
    def search_documents_enhanced(self, 
                                 query: str,
                                 method: str = "hybrid",
                                 domain_filter: Optional[str] = None,
                                 importance_filter: Optional[str] = None,
                                 regulation_filter: Optional[str] = None,
                                 top_k: int = 5) -> List[Dict[str, Any]]:
        """Enhanced 문서 검색"""
        try:
            if not self.is_initialized:
                return []
            
            results = self.enhanced_vector_engine.search_with_metadata_filters(
                query=query,
                domain_filter=domain_filter,
                importance_filter=importance_filter,
                regulation_filter=regulation_filter,
                top_k=top_k
            )
            
            # 결과를 더 풍부한 정보로 확장
            enhanced_results = []
            for result in results:
                enhanced_result = result.copy()
                
                # 관련 문서 정보 추가
                doc_id = result.get("id")
                if doc_id:
                    related = self.relationship_mapper.get_related_documents(
                        document_id=doc_id,
                        max_results=3
                    )
                    enhanced_result["related_documents"] = related
                
                enhanced_results.append(enhanced_result)
            
            return enhanced_results
            
        except Exception as e:
            self.logger.error(f"Enhanced 문서 검색 실패: {e}")
            return []
    
    def get_domain_overview(self, domain: str) -> Dict[str, Any]:
        """특정 도메인에 대한 개요 정보"""
        try:
            if not self.is_initialized:
                return {"error": "System not initialized"}
            
            # 도메인별 문서 검색
            domain_docs = self.enhanced_vector_engine.search_with_metadata_filters(
                query=domain,
                domain_filter=domain,
                top_k=20
            )
            
            if not domain_docs:
                return {"error": f"도메인 '{domain}'에 대한 문서를 찾을 수 없습니다"}
            
            # 도메인 통계 생성
            overview = {
                "domain": domain,
                "total_documents": len(domain_docs),
                "importance_distribution": {},
                "regulation_types": {},
                "key_topics": [],
                "representative_documents": []
            }
            
            # 통계 계산
            for doc in domain_docs:
                metadata = doc.get("metadata", {})
                
                importance = metadata.get("importance_level", "informational")
                regulation_type = metadata.get("regulation_type", "기타")
                
                overview["importance_distribution"][importance] = \
                    overview["importance_distribution"].get(importance, 0) + 1
                overview["regulation_types"][regulation_type] = \
                    overview["regulation_types"].get(regulation_type, 0) + 1
            
            # 대표 문서 선별 (높은 중요도 + 높은 유사도)
            representative = sorted(
                domain_docs[:10], 
                key=lambda x: (
                    1.0 if x.get("metadata", {}).get("importance_level") == "critical" else 0.5,
                    x.get("similarity", 0)
                ),
                reverse=True
            )[:5]
            
            overview["representative_documents"] = [
                {
                    "id": doc.get("id"),
                    "title": doc.get("metadata", {}).get("hierarchy_title", ""),
                    "similarity": doc.get("similarity", 0),
                    "importance": doc.get("metadata", {}).get("importance_level", "")
                }
                for doc in representative
            ]
            
            return overview
            
        except Exception as e:
            self.logger.error(f"도메인 개요 생성 실패: {e}")
            return {"error": str(e)}
    
    def get_enhanced_system_status(self) -> Dict[str, Any]:
        """Enhanced 시스템 상태 조회"""
        try:
            status = {
                "initialized": self.is_initialized,
                "config": self.config,
                "timestamp": datetime.now().isoformat()
            }
            
            if self.is_initialized:
                # Enhanced Vector Engine 통계
                if self.enhanced_vector_engine:
                    vector_stats = self.enhanced_vector_engine.get_statistics()
                    status["enhanced_vector_engine"] = vector_stats
                
                # Relationship Mapper 통계
                if self.relationship_mapper:
                    relationship_stats = self.relationship_mapper.get_statistics()
                    status["relationship_mapper"] = relationship_stats
                
                # Document Hierarchy Analyzer 통계
                if self.hierarchy_analyzer:
                    hierarchy_stats = self.hierarchy_analyzer.get_analysis_statistics()
                    status["hierarchy_analyzer"] = hierarchy_stats
            
            return status
            
        except Exception as e:
            self.logger.error(f"Enhanced 시스템 상태 조회 실패: {e}")
            return {"error": str(e)}
    
    def analyze_query_complexity(self, question: str) -> Dict[str, Any]:
        """질문 복잡도 분석"""
        try:
            # 질문 분석
            analysis = {
                "question": question,
                "length": len(question),
                "word_count": len(question.split()),
                "complexity_indicators": {
                    "has_multiple_concepts": len([word for word in question.split() if word in 
                        ["그리고", "또한", "및", "와", "과", "에서", "관련", "연관"]]) > 0,
                    "has_conditions": any(word in question for word in ["만약", "경우", "때", "조건"]),
                    "has_comparisons": any(word in question for word in ["차이", "비교", "대비", "보다"]),
                    "has_procedures": any(word in question for word in ["방법", "절차", "과정", "단계"]),
                    "has_temporal_aspects": any(word in question for word in ["언제", "시기", "이후", "이전", "동안"])
                },
                "recommended_search_strategy": "hybrid"
            }
            
            # 복잡도 기반 검색 전략 추천
            complexity_score = sum(analysis["complexity_indicators"].values())
            
            if complexity_score >= 3:
                analysis["recommended_search_strategy"] = "smart"
                analysis["recommended_filters"] = ["importance_filter:critical"]
            elif complexity_score >= 2:
                analysis["recommended_search_strategy"] = "hybrid"
                analysis["recommended_filters"] = ["domain_filter:추천"]
            else:
                analysis["recommended_search_strategy"] = "semantic"
                analysis["recommended_filters"] = []
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"질문 복잡도 분석 실패: {e}")
            return {"error": str(e)}


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """로깅 설정"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 기본 로깅 설정
    handlers = [logging.StreamHandler()]
    
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def main():
    """메인 실행 함수 (데모용)"""
    # 로깅 설정
    setup_logging("INFO", "logs/enhanced_rag_system.log")
    
    # Enhanced RAG 시스템 생성
    enhanced_rag = EnhancedPowerMarketRAG()
    
    print("=== Enhanced 전력시장 RAG 시스템 ===")
    print("1. 시스템 초기화 중...")
    
    # 초기화
    if enhanced_rag.initialize():
        print("✅ Enhanced 시스템 초기화 완료")
        
        # 상태 확인
        status = enhanced_rag.get_enhanced_system_status()
        print(f"📊 Enhanced 시스템 상태: 정상")
        
        # 테스트 질문들
        test_questions = [
            {
                "question": "하루전발전계획이 무엇인가요?",
                "domain_filter": "발전계획"
            },
            {
                "question": "계통운영의 기본 원칙은 무엇인가요?",
                "domain_filter": "계통운영",
                "importance_filter": "critical"
            },
            {
                "question": "전력시장에서 예비력의 역할과 송전제약의 관계는?",
                "include_relationships": True
            }
        ]
        
        print("\n2. Enhanced 테스트 질문 처리:")
        for i, test in enumerate(test_questions, 1):
            question = test.pop("question")
            print(f"\n[질문 {i}] {question}")
            
            # 질문 복잡도 분석
            complexity = enhanced_rag.analyze_query_complexity(question)
            print(f"복잡도: {sum(complexity['complexity_indicators'].values())}/5")
            
            # Enhanced 답변 생성
            result = enhanced_rag.ask_enhanced(question, **test)
            print(f"답변: {result['answer'][:150]}...")
            print(f"신뢰도: {result['confidence']:.3f}")
            print(f"검색 결과: {result['search_results']}개")
            if result.get('related_documents', 0) > 0:
                print(f"관련 문서: {result['related_documents']}개")
            
    else:
        print("❌ Enhanced 시스템 초기화 실패")


if __name__ == "__main__":
    main()