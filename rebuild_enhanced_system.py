"""
Enhanced RAG System Rebuilder
고도화된 RAG 시스템으로 벡터 DB 재구축
"""

import logging
import os
import yaml
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 고도화된 모듈들 import
from core.enhanced_vector_engine import EnhancedVectorEngine
from core.multimodal_processor import MultimodalProcessor
from core.document_hierarchy_analyzer import DocumentHierarchyAnalyzer
from core.relationship_mapper import PowerMarketRelationshipMapper
from embeddings.text_embedder import PowerMarketEmbedder

# 기존 모듈들
from data.vectors.vector_store import VectorDatabase

logger = logging.getLogger(__name__)


class EnhancedSystemRebuilder:
    """
    향상된 RAG 시스템 재구축기
    - 기존 데이터 백업
    - 고도화된 메타데이터로 재처리
    - 새로운 임베딩 모델 적용
    - 관계 매핑 구축
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.backup_dir = Path("backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 디렉토리 생성
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 구성 요소들
        self.multimodal_processor = None
        self.enhanced_engine = None
        self.hierarchy_analyzer = None
        self.relationship_mapper = None
        
        # 재구축 통계
        self.rebuild_stats = {
            "start_time": None,
            "end_time": None,
            "documents_processed": 0,
            "chunks_created": 0,
            "relationships_mapped": 0,
            "errors": []
        }
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"설정 파일 로드 완료: {config_path}")
            return config
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            # 기본 설정 반환
            return {
                "EMBEDDING_MODEL": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                "VECTOR_DB_PATH": "./vector_db",
                "COLLECTION_NAME": "power_market_docs_enhanced",
                "CHUNK_SIZE": 1000,
                "CHUNK_OVERLAP": 200
            }
    
    def rebuild_system(self, documents_dir: str = "documents", force_rebuild: bool = False) -> bool:
        """
        전체 시스템 재구축
        
        Args:
            documents_dir: 문서 디렉토리
            force_rebuild: 강제 재구축 여부
            
        Returns:
            성공 여부
        """
        logger.info("Enhanced RAG 시스템 재구축 시작")
        self.rebuild_stats["start_time"] = datetime.now().isoformat()
        
        try:
            # 1. 사전 검사
            if not self._pre_rebuild_checks(documents_dir, force_rebuild):
                return False
            
            # 2. 기존 데이터 백업
            if not self._backup_existing_data():
                logger.warning("백업 실패했지만 재구축 계속 진행")
            
            # 3. 구성 요소 초기화
            if not self._initialize_components():
                return False
            
            # 4. 문서 처리 및 벡터화
            processed_docs = self._process_all_documents(documents_dir)
            if not processed_docs:
                logger.error("문서 처리 실패")
                return False
            
            # 5. 관계 매핑
            relationships = self._build_document_relationships(processed_docs)
            
            # 6. 벡터 DB 구축
            if not self._build_vector_database(processed_docs):
                return False
            
            # 7. 관계 정보 저장
            self._save_relationships(relationships)
            
            # 8. 시스템 검증
            if not self._validate_rebuilt_system():
                logger.warning("시스템 검증에서 일부 문제 발견")
            
            # 9. 통계 및 보고서 생성
            self._generate_rebuild_report()
            
            logger.info("Enhanced RAG 시스템 재구축 완료")
            return True
            
        except Exception as e:
            logger.error(f"시스템 재구축 실패: {e}")
            self.rebuild_stats["errors"].append(str(e))
            return False
        finally:
            self.rebuild_stats["end_time"] = datetime.now().isoformat()
    
    def _pre_rebuild_checks(self, documents_dir: str, force_rebuild: bool) -> bool:
        """재구축 전 검사"""
        logger.info("재구축 전 검사 수행")
        
        # 문서 디렉토리 존재 확인
        if not os.path.exists(documents_dir):
            logger.error(f"문서 디렉토리가 존재하지 않습니다: {documents_dir}")
            return False
        
        # 문서 파일 확인
        doc_files = list(Path(documents_dir).rglob("*.pdf")) + list(Path(documents_dir).rglob("*.txt"))
        if not doc_files:
            logger.error(f"처리할 문서가 없습니다: {documents_dir}")
            return False
        
        logger.info(f"처리할 문서 수: {len(doc_files)}")
        
        # 기존 벡터 DB 확인
        vector_db_path = self.config.get("VECTOR_DB_PATH", "./vector_db")
        if os.path.exists(vector_db_path) and not force_rebuild:
            response = input(f"기존 벡터 DB가 존재합니다 ({vector_db_path}). 계속하시겠습니까? (y/n): ")
            if response.lower() != 'y':
                logger.info("사용자에 의해 재구축 취소")
                return False
        
        return True
    
    def _backup_existing_data(self) -> bool:
        """기존 데이터 백업"""
        logger.info("기존 데이터 백업 중...")
        
        try:
            # 벡터 DB 백업
            vector_db_path = Path(self.config.get("VECTOR_DB_PATH", "./vector_db"))
            if vector_db_path.exists():
                backup_vector_path = self.backup_dir / "vector_db"
                shutil.copytree(vector_db_path, backup_vector_path)
                logger.info(f"벡터 DB 백업 완료: {backup_vector_path}")
            
            # 메타데이터 백업
            metadata_path = Path("data/metadata")
            if metadata_path.exists():
                backup_metadata_path = self.backup_dir / "metadata"
                shutil.copytree(metadata_path, backup_metadata_path)
                logger.info(f"메타데이터 백업 완료: {backup_metadata_path}")
            
            # 로그 백업
            logs_path = Path("logs")
            if logs_path.exists():
                backup_logs_path = self.backup_dir / "logs"
                shutil.copytree(logs_path, backup_logs_path)
                logger.info(f"로그 백업 완료: {backup_logs_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"백업 실패: {e}")
            return False
    
    def _initialize_components(self) -> bool:
        """구성 요소들 초기화"""
        logger.info("고도화된 구성 요소들 초기화 중...")
        
        try:
            # 1. Multimodal Processor
            self.multimodal_processor = MultimodalProcessor()
            
            # 2. Enhanced Vector Engine
            self.enhanced_engine = EnhancedVectorEngine(self.config)
            
            # 3. Document Hierarchy Analyzer
            self.hierarchy_analyzer = DocumentHierarchyAnalyzer()
            
            # 4. Relationship Mapper
            embedder = PowerMarketEmbedder(self.config.get("EMBEDDING_MODEL"))
            self.relationship_mapper = PowerMarketRelationshipMapper(embedder)
            
            logger.info("모든 구성 요소 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"구성 요소 초기화 실패: {e}")
            return False
    
    def _process_all_documents(self, documents_dir: str) -> List[Dict[str, Any]]:
        """모든 문서 처리"""
        logger.info("문서 처리 시작")
        
        processed_docs = []
        doc_files = list(Path(documents_dir).rglob("*.pdf")) + list(Path(documents_dir).rglob("*.txt"))
        
        for i, doc_file in enumerate(doc_files, 1):
            try:
                logger.info(f"문서 처리 중 ({i}/{len(doc_files)}): {doc_file.name}")
                
                # 1. Multimodal 처리
                processed_doc = self.multimodal_processor.process_document(str(doc_file))
                
                if not processed_doc:
                    logger.warning(f"문서 처리 실패: {doc_file}")
                    continue
                
                # 2. 계층 구조 분석
                hierarchy_analysis = self.hierarchy_analyzer.analyze_document_structure(processed_doc)
                processed_doc["hierarchy_analysis"] = hierarchy_analysis
                
                # 3. Enhanced Vector Engine으로 메타데이터 강화 및 청킹
                enhanced_chunks = self.enhanced_engine.process_document_with_metadata(processed_doc)
                
                # 처리된 청크들을 문서와 함께 저장
                processed_doc["enhanced_chunks"] = enhanced_chunks
                processed_docs.append(processed_doc)
                
                self.rebuild_stats["documents_processed"] += 1
                self.rebuild_stats["chunks_created"] += len(enhanced_chunks)
                
            except Exception as e:
                error_msg = f"문서 처리 오류 ({doc_file}): {e}"
                logger.error(error_msg)
                self.rebuild_stats["errors"].append(error_msg)
                continue
        
        logger.info(f"문서 처리 완료: {len(processed_docs)}개 문서, {self.rebuild_stats['chunks_created']}개 청크")
        return processed_docs
    
    def _build_document_relationships(self, processed_docs: List[Dict[str, Any]]) -> List[Any]:
        """문서 간 관계 구축"""
        logger.info("문서 간 관계 매핑 시작")
        
        try:
            # 모든 청크들 수집
            all_chunks = []
            for doc in processed_docs:
                chunks = doc.get("enhanced_chunks", [])
                all_chunks.extend(chunks)
            
            # 관계 분석
            relationships = self.relationship_mapper.analyze_document_relationships(all_chunks)
            
            self.rebuild_stats["relationships_mapped"] = len(relationships)
            logger.info(f"관계 매핑 완료: {len(relationships)}개 관계")
            
            return relationships
            
        except Exception as e:
            logger.error(f"관계 매핑 실패: {e}")
            return []
    
    def _build_vector_database(self, processed_docs: List[Dict[str, Any]]) -> bool:
        """벡터 데이터베이스 구축"""
        logger.info("벡터 데이터베이스 구축 시작")
        
        try:
            # 기존 벡터 DB 초기화
            vector_db = VectorDatabase(
                db_path=self.config.get("VECTOR_DB_PATH", "./vector_db"),
                collection_name=self.config.get("COLLECTION_NAME", "power_market_docs_enhanced")
            )
            vector_db.clear_collection()
            
            # 모든 enhanced chunks 수집
            all_enhanced_chunks = []
            for doc in processed_docs:
                chunks = doc.get("enhanced_chunks", [])
                all_enhanced_chunks.extend(chunks)
            
            # Enhanced Vector Engine을 통해 저장
            success = self.enhanced_engine.store_enhanced_documents(all_enhanced_chunks)
            
            if success:
                logger.info("벡터 데이터베이스 구축 완료")
                return True
            else:
                logger.error("벡터 데이터베이스 구축 실패")
                return False
                
        except Exception as e:
            logger.error(f"벡터 데이터베이스 구축 오류: {e}")
            return False
    
    def _save_relationships(self, relationships: List[Any]):
        """관계 정보 저장"""
        logger.info("관계 정보 저장 중...")
        
        try:
            # 관계 정보를 JSON으로 저장
            relationships_dir = Path("data/relationships")
            relationships_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            relationships_file = relationships_dir / f"relationships_{timestamp}.json"
            
            relationships_data = self.relationship_mapper.export_relationships("json")
            
            with open(relationships_file, "w", encoding="utf-8") as f:
                f.write(relationships_data)
            
            # 관계 그래프도 저장
            if relationships:
                graph_data = self.relationship_mapper.build_relationship_graph(relationships)
                graph_file = relationships_dir / f"relationship_graph_{timestamp}.json"
                
                with open(graph_file, "w", encoding="utf-8") as f:
                    json.dump(graph_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"관계 정보 저장 완료: {relationships_file}")
            
        except Exception as e:
            logger.error(f"관계 정보 저장 실패: {e}")
    
    def _validate_rebuilt_system(self) -> bool:
        """재구축된 시스템 검증"""
        logger.info("시스템 검증 중...")
        
        try:
            # 벡터 DB 상태 확인
            stats = self.enhanced_engine.get_statistics()
            vector_stats = stats.get("vector_db_stats", {})
            
            doc_count = vector_stats.get("document_count", 0)
            if doc_count == 0:
                logger.error("벡터 DB에 문서가 없습니다")
                return False
            
            logger.info(f"벡터 DB 문서 수: {doc_count}")
            
            # 간단한 검색 테스트
            test_queries = [
                "발전계획이란 무엇인가요?",
                "계통운영의 기본 원칙은?",
                "전력시장에서 예비력의 역할은?"
            ]
            
            for query in test_queries:
                try:
                    results = self.enhanced_engine.search_with_metadata_filters(
                        query=query,
                        top_k=3
                    )
                    
                    if results:
                        logger.info(f"검색 테스트 성공: '{query}' -> {len(results)}개 결과")
                    else:
                        logger.warning(f"검색 테스트 결과 없음: '{query}'")
                        
                except Exception as e:
                    logger.error(f"검색 테스트 실패: '{query}' -> {e}")
                    return False
            
            logger.info("시스템 검증 완료")
            return True
            
        except Exception as e:
            logger.error(f"시스템 검증 오류: {e}")
            return False
    
    def _generate_rebuild_report(self):
        """재구축 보고서 생성"""
        logger.info("재구축 보고서 생성 중...")
        
        try:
            # 통계 정보 수집
            vector_stats = self.enhanced_engine.get_statistics()
            relationship_stats = self.relationship_mapper.get_statistics()
            
            # 처리 시간 계산
            start_time = datetime.fromisoformat(self.rebuild_stats["start_time"])
            end_time = datetime.fromisoformat(self.rebuild_stats["end_time"])
            processing_time = (end_time - start_time).total_seconds()
            
            report = {
                "rebuild_summary": {
                    "timestamp": self.rebuild_stats["end_time"],
                    "processing_time_seconds": processing_time,
                    "documents_processed": self.rebuild_stats["documents_processed"],
                    "chunks_created": self.rebuild_stats["chunks_created"],
                    "relationships_mapped": self.rebuild_stats["relationships_mapped"],
                    "errors_count": len(self.rebuild_stats["errors"])
                },
                "vector_database_stats": vector_stats,
                "relationship_stats": relationship_stats,
                "configuration": self.config,
                "errors": self.rebuild_stats["errors"]
            }
            
            # 보고서 저장
            reports_dir = Path("reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = reports_dir / f"rebuild_report_{timestamp}.json"
            
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            # 콘솔에 요약 출력
            print("\n" + "="*60)
            print("Enhanced RAG 시스템 재구축 완료")
            print("="*60)
            print(f"처리 시간: {processing_time:.1f}초")
            print(f"처리된 문서: {self.rebuild_stats['documents_processed']}개")
            print(f"생성된 청크: {self.rebuild_stats['chunks_created']}개")
            print(f"매핑된 관계: {self.rebuild_stats['relationships_mapped']}개")
            print(f"오류 수: {len(self.rebuild_stats['errors'])}개")
            print(f"상세 보고서: {report_file}")
            print("="*60)
            
            logger.info(f"재구축 보고서 저장 완료: {report_file}")
            
        except Exception as e:
            logger.error(f"보고서 생성 실패: {e}")


def setup_logging():
    """로깅 설정"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"rebuild_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def main():
    """메인 실행 함수"""
    setup_logging()
    
    print("Enhanced RAG 시스템 재구축기")
    print("="*50)
    
    # 명령행 인수 처리
    import argparse
    parser = argparse.ArgumentParser(description="Enhanced RAG System Rebuilder")
    parser.add_argument("--documents", default="documents", help="문서 디렉토리 경로")
    parser.add_argument("--config", default="config/config.yaml", help="설정 파일 경로")
    parser.add_argument("--force", action="store_true", help="강제 재구축")
    
    args = parser.parse_args()
    
    # 재구축기 생성 및 실행
    rebuilder = EnhancedSystemRebuilder(config_path=args.config)
    
    success = rebuilder.rebuild_system(
        documents_dir=args.documents,
        force_rebuild=args.force
    )
    
    if success:
        print("\n✅ Enhanced RAG 시스템 재구축이 성공적으로 완료되었습니다!")
        return 0
    else:
        print("\n❌ Enhanced RAG 시스템 재구축에 실패했습니다.")
        return 1


if __name__ == "__main__":
    exit(main())