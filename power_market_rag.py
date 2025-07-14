"""
전력시장 RAG 시스템 메인 모듈
- 모든 구성 요소를 통합하여 완전한 RAG 시스템 제공
- 문서 처리부터 답변 생성까지 전체 파이프라인 관리
"""

import logging
import os
import yaml
from typing import List, Dict, Optional
from pathlib import Path

# 각 모듈 임포트
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 각 모듈 임포트
from embeddings.document_processor import DocumentProcessor
from embeddings.text_embedder import PowerMarketEmbedder
from vector_db.vector_store import VectorDatabase
from retrieval.document_retriever import PowerMarketRetriever
from generation.answer_generator import PowerMarketAnswerGenerator

class PowerMarketRAG:
    """전력시장 특화 RAG 시스템 메인 클래스"""
    
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
        
        # 구성 요소들
        self.document_processor = None
        self.text_embedder = None
        self.vector_db = None
        self.retriever = None
        self.answer_generator = None
        
        self.logger.info("PowerMarketRAG 시스템이 생성되었습니다")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """설정 파일 로드"""
        if config_path is None:
            config_path = "config/config.yaml"
        
        default_config = {
            "VECTOR_DB_TYPE": "chromadb",
            "VECTOR_DB_PATH": "./vector_db",
            "COLLECTION_NAME": "power_market_docs",
            "EMBEDDING_MODEL": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
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
            self.logger.info("RAG 시스템 초기화 시작")
            
            # 1. 문서 처리기 초기화
            self.logger.info("문서 처리기 초기화 중...")
            self.document_processor = DocumentProcessor(
                chunk_size=self.config["CHUNK_SIZE"],
                chunk_overlap=self.config["CHUNK_OVERLAP"]
            )
            
            # 2. 텍스트 임베딩 모델 초기화
            self.logger.info("임베딩 모델 초기화 중...")
            self.text_embedder = PowerMarketEmbedder(
                model_name=self.config["EMBEDDING_MODEL"]
            )
            
            # 3. 벡터 데이터베이스 초기화
            self.logger.info("벡터 데이터베이스 초기화 중...")
            self.vector_db = VectorDatabase(
                db_path=self.config["VECTOR_DB_PATH"],
                collection_name=self.config["COLLECTION_NAME"]
            )
            
            # 4. 검색 엔진 초기화
            self.logger.info("검색 엔진 초기화 중...")
            self.retriever = PowerMarketRetriever(
                vector_db=self.vector_db,
                text_embedder=self.text_embedder,
                top_k=self.config["TOP_K"],
                similarity_threshold=self.config["SIMILARITY_THRESHOLD"]
            )
            
            # 5. 답변 생성기 초기화
            self.logger.info("답변 생성기 초기화 중...")
            self.answer_generator = PowerMarketAnswerGenerator()
            
            self.is_initialized = True
            self.logger.info("RAG 시스템 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"RAG 시스템 초기화 실패: {e}")
            return False
    
    def load_documents(self, documents_dir: str) -> bool:
        """문서 디렉토리에서 모든 문서 로드 및 인덱싱"""
        try:
            if not self.is_initialized:
                self.logger.error("시스템이 초기화되지 않았습니다")
                return False
            
            self.logger.info(f"문서 로딩 시작: {documents_dir}")
            
            # 1. 문서 처리 (텍스트 추출 및 청킹)
            chunks = self.document_processor.process_documents_from_directory(documents_dir)
            
            if not chunks:
                self.logger.warning("처리된 문서가 없습니다")
                return False
            
            # 2. 임베딩 생성
            self.logger.info("문서 임베딩 생성 중...")
            embedded_chunks = self.text_embedder.encode_documents(chunks)
            
            # 3. 벡터 데이터베이스에 저장
            self.logger.info("벡터 데이터베이스에 저장 중...")
            success = self.vector_db.add_documents(embedded_chunks)
            
            if success:
                stats = self.vector_db.get_collection_stats()
                self.logger.info(f"문서 로딩 완료: {stats}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"문서 로딩 실패: {e}")
            return False
    
    def ask(self, question: str, search_method: str = "hybrid") -> Dict:
        """질문에 대한 답변 생성"""
        try:
            if not self.is_initialized:
                return {
                    "answer": "시스템이 초기화되지 않았습니다.",
                    "confidence": 0.0,
                    "sources": [],
                    "error": "System not initialized"
                }
            
            self.logger.info(f"질문 처리 시작: {question}")
            
            # 1. 관련 문서 검색
            if search_method == "semantic":
                search_results = self.retriever.semantic_search(question)
            elif search_method == "keyword":
                search_results = self.retriever.keyword_search(question)
            elif search_method == "hybrid":
                search_results = self.retriever.hybrid_search(question)
            elif search_method == "smart":
                search_results = self.retriever.smart_search(question)
            else:
                search_results = self.retriever.hybrid_search(question)
            
            if not search_results:
                return {
                    "answer": "관련 문서를 찾을 수 없습니다.",
                    "confidence": 0.0,
                    "sources": [],
                    "search_results": 0
                }
            
            # 2. 컨텍스트 생성
            context = self.retriever.get_context_for_generation(search_results)
            sources = [result.source_file for result in search_results]
            
            # 3. 답변 생성
            generation_result = self.answer_generator.generate_answer(
                context=context,
                query=question,
                sources=sources
            )
            
            # 4. 결과 반환
            result = {
                "answer": generation_result.answer,
                "confidence": generation_result.confidence,
                "sources": generation_result.sources,
                "reasoning": generation_result.reasoning,
                "metadata": generation_result.metadata,
                "search_results": len(search_results),
                "search_method": search_method
            }
            
            self.logger.info(f"질문 처리 완료 (신뢰도: {generation_result.confidence:.3f})")
            return result
            
        except Exception as e:
            self.logger.error(f"질문 처리 실패: {e}")
            return {
                "answer": "답변 생성 중 오류가 발생했습니다.",
                "confidence": 0.0,
                "sources": [],
                "error": str(e)
            }
    
    def get_system_status(self) -> Dict:
        """시스템 상태 조회"""
        try:
            status = {
                "initialized": self.is_initialized,
                "config": self.config
            }
            
            if self.is_initialized and self.vector_db:
                stats = self.vector_db.get_collection_stats()
                status.update(stats)
            
            return status
            
        except Exception as e:
            self.logger.error(f"시스템 상태 조회 실패: {e}")
            return {"error": str(e)}
    
    def search_documents(self, query: str, method: str = "hybrid", top_k: int = 5) -> List[Dict]:
        """문서 검색만 수행 (답변 생성 없이)"""
        try:
            if not self.is_initialized:
                return []
            
            if method == "semantic":
                results = self.retriever.semantic_search(query, top_k)
            elif method == "keyword":
                results = self.retriever.keyword_search(query, top_k)
            elif method == "hybrid":
                results = self.retriever.hybrid_search(query, top_k=top_k)
            elif method == "smart":
                results = self.retriever.smart_search(query, top_k)
            else:
                results = self.retriever.hybrid_search(query, top_k=top_k)
            
            # 결과를 딕셔너리 형태로 변환
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "text": result.text,
                    "similarity": result.similarity,
                    "source_file": result.source_file,
                    "metadata": result.metadata
                })
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"문서 검색 실패: {e}")
            return []
    
    def clear_database(self) -> bool:
        """벡터 데이터베이스 초기화"""
        try:
            if self.vector_db:
                return self.vector_db.clear_collection()
            return False
        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 실패: {e}")
            return False

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
    """메인 실행 함수 (테스트용)"""
    # 로깅 설정
    setup_logging("INFO", "logs/rag_system.log")
    
    # RAG 시스템 생성
    rag_system = PowerMarketRAG()
    
    print("=== 전력시장 RAG 시스템 ===")
    print("1. 시스템 초기화 중...")
    
    # 초기화
    if rag_system.initialize():
        print("✅ 시스템 초기화 완료")
        
        # 상태 확인
        status = rag_system.get_system_status()
        print(f"📊 시스템 상태: {status}")
        
        # 문서 로딩 (documents 폴더가 있는 경우)
        documents_dir = "documents"
        if os.path.exists(documents_dir):
            print(f"2. 문서 로딩 중: {documents_dir}")
            if rag_system.load_documents(documents_dir):
                print("✅ 문서 로딩 완료")
            else:
                print("❌ 문서 로딩 실패")
        else:
            print(f"📁 문서 디렉토리가 없습니다: {documents_dir}")
        
        # 테스트 질문
        test_questions = [
            "하루전발전계획이 무엇인가요?",
            "계통운영의 기본 원칙은 무엇인가요?",
            "전력시장에서 예비력의 역할은?",
        ]
        
        print("\n3. 테스트 질문 처리:")
        for question in test_questions:
            print(f"\n질문: {question}")
            result = rag_system.ask(question)
            print(f"답변: {result['answer'][:200]}...")
            print(f"신뢰도: {result['confidence']:.3f}")
            
    else:
        print("❌ 시스템 초기화 실패")

if __name__ == "__main__":
    main()
