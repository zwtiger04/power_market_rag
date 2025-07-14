#!/usr/bin/env python3
"""
멀티모달 시스템 통합 테스트
실제 전력시장 문서로 전체 파이프라인 검증
"""

import sys
import logging
from pathlib import Path
import time
import json
from typing import List, Dict, Any

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from core.multimodal_processor import get_multimodal_processor
from core.metadata_extractor import get_metadata_extractor
from core.vector_engine import get_vector_engine

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_multimodal.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class MultimodalSystemTester:
    """멀티모달 시스템 통합 테스터"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.documents_dir = self.data_dir / "documents"
        self.results_dir = self.data_dir / "test_results"
        
        # 결과 디렉토리 생성
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 컴포넌트 초기화
        self.multimodal_processor = get_multimodal_processor(data_dir)
        self.metadata_extractor = get_metadata_extractor(data_dir)
        self.vector_engine = get_vector_engine(data_dir)
        
        # 테스트 결과 저장
        self.test_results = {
            "start_time": None,
            "end_time": None,
            "total_duration_ms": 0,
            "documents_tested": [],
            "component_performance": {},
            "errors": [],
            "summary": {}
        }
    
    def run_comprehensive_test(self, max_documents: int = 3) -> Dict[str, Any]:
        """포괄적인 시스템 테스트 실행"""
        logger.info("멀티모달 시스템 통합 테스트 시작")
        self.test_results["start_time"] = time.time()
        
        try:
            # 1. 의존성 확인
            self._check_dependencies()
            
            # 2. 문서 선택
            test_documents = self._select_test_documents(max_documents)
            
            # 3. 각 문서별 전체 파이프라인 테스트
            for doc_path in test_documents:
                self._test_document_pipeline(doc_path)
            
            # 4. 검색 성능 테스트
            self._test_search_performance()
            
            # 5. 결과 정리 및 저장
            self._finalize_test_results()
            
            logger.info("멀티모달 시스템 통합 테스트 완료")
            return self.test_results
            
        except Exception as e:
            logger.error(f"테스트 실행 중 오류: {e}")
            self.test_results["errors"].append(str(e))
            return self.test_results
    
    def _check_dependencies(self):
        """의존성 확인"""
        logger.info("시스템 의존성 확인 중...")
        
        dependencies = {
            "multimodal_processor": self.multimodal_processor is not None,
            "metadata_extractor": self.metadata_extractor is not None,
            "vector_engine": self.vector_engine is not None,
            "documents_dir_exists": self.documents_dir.exists(),
            "has_pdf_files": len(list(self.documents_dir.glob("*.pdf"))) > 0
        }
        
        for dep, status in dependencies.items():
            if not status:
                raise Exception(f"의존성 확인 실패: {dep}")
        
        logger.info("모든 의존성 확인 완료")
    
    def _select_test_documents(self, max_documents: int) -> List[Path]:
        """테스트할 문서 선택"""
        pdf_files = list(self.documents_dir.glob("*.pdf"))
        
        # 작은 문서부터 선택 (테스트 효율성을 위해)
        pdf_files_with_size = [(f, f.stat().st_size) for f in pdf_files]
        pdf_files_with_size.sort(key=lambda x: x[1])  # 크기순 정렬
        
        selected = [f[0] for f in pdf_files_with_size[:max_documents]]
        
        logger.info(f"테스트 문서 선택: {[f.name for f in selected]}")
        return selected
    
    def _test_document_pipeline(self, doc_path: Path):
        """단일 문서에 대한 전체 파이프라인 테스트"""
        logger.info(f"문서 파이프라인 테스트 시작: {doc_path.name}")
        
        doc_result = {
            "document_path": str(doc_path),
            "document_name": doc_path.name,
            "file_size_bytes": doc_path.stat().st_size,
            "stages": {},
            "total_processing_time_ms": 0,
            "success": False,
            "error": None
        }
        
        start_time = time.time()
        
        try:
            # Stage 1: Multimodal Processing
            stage_start = time.time()
            logger.info(f"Stage 1: 멀티모달 처리 - {doc_path.name}")
            
            processed_doc = self.multimodal_processor.process_document(doc_path)
            
            stage_duration = (time.time() - stage_start) * 1000
            doc_result["stages"]["multimodal_processing"] = {
                "duration_ms": stage_duration,
                "success": "error" not in processed_doc,
                "sections_extracted": len(processed_doc.get("content", {}).get("sections", [])),
                "paragraphs_extracted": len(processed_doc.get("content", {}).get("paragraphs", [])),
                "images_extracted": len(processed_doc.get("multimodal_content", {}).get("images", [])),
                "tables_extracted": len(processed_doc.get("multimodal_content", {}).get("tables", [])),
                "formulas_extracted": len(processed_doc.get("multimodal_content", {}).get("formulas", []))
            }
            
            if "error" in processed_doc:
                raise Exception(f"멀티모달 처리 실패: {processed_doc['error']}")
            
            # Stage 2: Metadata Extraction
            stage_start = time.time()
            logger.info(f"Stage 2: 메타데이터 추출 - {doc_path.name}")
            
            metadata = self.metadata_extractor.extract_metadata(processed_doc)
            
            stage_duration = (time.time() - stage_start) * 1000
            doc_result["stages"]["metadata_extraction"] = {
                "duration_ms": stage_duration,
                "success": "error" not in metadata,
                "entities_extracted": self._count_entities(metadata),
                "keywords_extracted": len(metadata.get("content_metadata", {}).get("keyword_analysis", {}).get("top_keywords", [])),
                "relationships_found": len(metadata.get("relationships", [])),
                "quality_score": metadata.get("quality_indicators", {}).get("overall_quality", 0)
            }
            
            if "error" in metadata:
                raise Exception(f"메타데이터 추출 실패: {metadata['error']}")
            
            # Stage 3: Vector Engine Integration
            stage_start = time.time()
            logger.info(f"Stage 3: 벡터 엔진 통합 - {doc_path.name}")
            
            # 문서를 벡터 엔진에 추가
            doc_id = processed_doc["document_id"]
            content = processed_doc["content"]
            doc_metadata = {
                "file_name": doc_path.name,
                "file_size": doc_path.stat().st_size,
                "processing_date": processed_doc["processed_at"],
                **metadata.get("power_market_metadata", {}).get("document_classification", {})
            }
            
            vector_success = self.vector_engine.add_document(doc_id, content, doc_metadata)
            
            stage_duration = (time.time() - stage_start) * 1000
            doc_result["stages"]["vector_integration"] = {
                "duration_ms": stage_duration,
                "success": vector_success,
                "document_added": vector_success
            }
            
            if not vector_success:
                raise Exception("벡터 엔진 통합 실패")
            
            # 전체 성공
            doc_result["success"] = True
            doc_result["total_processing_time_ms"] = (time.time() - start_time) * 1000
            
            # 결과 저장
            self._save_document_results(doc_id, processed_doc, metadata)
            
            logger.info(f"문서 파이프라인 테스트 성공: {doc_path.name} ({doc_result['total_processing_time_ms']:.2f}ms)")
            
        except Exception as e:
            doc_result["error"] = str(e)
            doc_result["total_processing_time_ms"] = (time.time() - start_time) * 1000
            logger.error(f"문서 파이프라인 테스트 실패: {doc_path.name} - {e}")
        
        self.test_results["documents_tested"].append(doc_result)
    
    def _test_search_performance(self):
        """검색 성능 테스트"""
        logger.info("검색 성능 테스트 시작")
        
        search_queries = [
            "전력시장 운영",
            "발전사업자",
            "시스템한계가격",
            "급전지시",
            "보조서비스",
            "정산 절차"
        ]
        
        search_results = {
            "queries_tested": len(search_queries),
            "total_search_time_ms": 0,
            "average_search_time_ms": 0,
            "successful_searches": 0,
            "query_results": []
        }
        
        start_time = time.time()
        
        for query in search_queries:
            query_start = time.time()
            
            try:
                result = self.vector_engine.search(
                    query=query,
                    search_type="hybrid",
                    level="all",
                    top_k=5,
                    ai_friendly=True
                )
                
                query_duration = (time.time() - query_start) * 1000
                
                query_result = {
                    "query": query,
                    "duration_ms": query_duration,
                    "success": "error" not in result,
                    "results_count": len(result.get("primary_results", [])),
                    "total_results": result.get("search_metadata", {}).get("total_results", 0)
                }
                
                if "error" not in result:
                    search_results["successful_searches"] += 1
                
                search_results["query_results"].append(query_result)
                
                logger.info(f"검색 쿼리 '{query}': {query_duration:.2f}ms, {query_result['total_results']}개 결과")
                
            except Exception as e:
                logger.error(f"검색 쿼리 '{query}' 실패: {e}")
        
        search_results["total_search_time_ms"] = (time.time() - start_time) * 1000
        search_results["average_search_time_ms"] = search_results["total_search_time_ms"] / len(search_queries)
        
        self.test_results["component_performance"]["search"] = search_results
        
        logger.info(f"검색 성능 테스트 완료: 평균 {search_results['average_search_time_ms']:.2f}ms")
    
    def _count_entities(self, metadata: Dict[str, Any]) -> int:
        """메타데이터에서 추출된 엔티티 수 계산"""
        entities = metadata.get("power_market_metadata", {}).get("market_entities", {})
        return sum(len(entity_list) for entity_list in entities.values())
    
    def _save_document_results(self, doc_id: str, processed_doc: Dict[str, Any], metadata: Dict[str, Any]):
        """문서별 결과 저장"""
        try:
            # 처리된 문서 저장
            self.multimodal_processor.save_processed_document(processed_doc)
            
            # 메타데이터 저장
            self.metadata_extractor.save_metadata(metadata)
            
            # 벡터 엔진 메타데이터 저장
            self.vector_engine.save_metadata()
            
        except Exception as e:
            logger.warning(f"문서 결과 저장 실패 {doc_id}: {e}")
    
    def _finalize_test_results(self):
        """테스트 결과 정리"""
        self.test_results["end_time"] = time.time()
        self.test_results["total_duration_ms"] = (
            self.test_results["end_time"] - self.test_results["start_time"]
        ) * 1000
        
        # 성공률 계산
        total_docs = len(self.test_results["documents_tested"])
        successful_docs = len([d for d in self.test_results["documents_tested"] if d["success"]])
        
        # 컴포넌트별 통계
        multimodal_stats = self.multimodal_processor.get_processing_stats()
        metadata_stats = self.metadata_extractor.get_extraction_stats()
        vector_stats = self.vector_engine.get_statistics()
        
        self.test_results["summary"] = {
            "total_documents": total_docs,
            "successful_documents": successful_docs,
            "success_rate": (successful_docs / total_docs * 100) if total_docs > 0 else 0,
            "total_processing_time_ms": self.test_results["total_duration_ms"],
            "average_processing_time_per_doc_ms": (
                self.test_results["total_duration_ms"] / total_docs
            ) if total_docs > 0 else 0,
            "component_stats": {
                "multimodal_processor": multimodal_stats,
                "metadata_extractor": metadata_stats,
                "vector_engine": vector_stats
            }
        }
        
        # 결과 파일로 저장
        results_file = self.results_dir / f"test_results_{int(time.time())}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"테스트 결과 저장: {results_file}")
    
    def print_summary(self):
        """테스트 결과 요약 출력"""
        summary = self.test_results.get("summary", {})
        
        print("\n" + "="*80)
        print("멀티모달 시스템 통합 테스트 결과 요약")
        print("="*80)
        
        print(f"📊 전체 통계:")
        print(f"  - 테스트 문서 수: {summary.get('total_documents', 0)}")
        print(f"  - 성공한 문서 수: {summary.get('successful_documents', 0)}")
        print(f"  - 성공률: {summary.get('success_rate', 0):.1f}%")
        print(f"  - 전체 처리 시간: {summary.get('total_processing_time_ms', 0):.2f}ms")
        print(f"  - 문서당 평균 처리 시간: {summary.get('average_processing_time_per_doc_ms', 0):.2f}ms")
        
        print(f"\n🔧 컴포넌트별 성능:")
        component_stats = summary.get("component_stats", {})
        
        # 멀티모달 프로세서
        mm_stats = component_stats.get("multimodal_processor", {})
        print(f"  📄 멀티모달 프로세서:")
        print(f"    - 처리된 문서: {mm_stats.get('processed_documents', 0)}")
        print(f"    - 추출된 이미지: {mm_stats.get('extracted_images', 0)}")
        print(f"    - 추출된 표: {mm_stats.get('extracted_tables', 0)}")
        print(f"    - 추출된 수식: {mm_stats.get('extracted_formulas', 0)}")
        
        # 메타데이터 추출기
        md_stats = component_stats.get("metadata_extractor", {})
        print(f"  🏷️  메타데이터 추출기:")
        print(f"    - 처리된 문서: {md_stats.get('documents_processed', 0)}")
        print(f"    - 추출된 엔티티: {md_stats.get('entities_extracted', 0)}")
        print(f"    - 추출된 키워드: {md_stats.get('keywords_extracted', 0)}")
        print(f"    - 매핑된 관계: {md_stats.get('relations_mapped', 0)}")
        
        # 벡터 엔진
        ve_stats = component_stats.get("vector_engine", {})
        print(f"  🔍 벡터 엔진:")
        collections = ve_stats.get("collections", {})
        for collection_name, collection_info in collections.items():
            print(f"    - {collection_name}: {collection_info.get('count', 0)}개 항목")
        
        # 검색 성능
        search_stats = self.test_results.get("component_performance", {}).get("search", {})
        if search_stats:
            print(f"  🔎 검색 성능:")
            print(f"    - 테스트 쿼리 수: {search_stats.get('queries_tested', 0)}")
            print(f"    - 성공한 검색: {search_stats.get('successful_searches', 0)}")
            print(f"    - 평균 검색 시간: {search_stats.get('average_search_time_ms', 0):.2f}ms")
        
        # 오류 정보
        errors = self.test_results.get("errors", [])
        if errors:
            print(f"\n❌ 오류 ({len(errors)}개):")
            for i, error in enumerate(errors[:5], 1):  # 최대 5개만 표시
                print(f"  {i}. {error}")
            if len(errors) > 5:
                print(f"  ... 및 {len(errors) - 5}개 추가 오류")
        
        print("\n" + "="*80)


def main():
    """메인 실행 함수"""
    print("멀티모달 시스템 통합 테스트 시작")
    
    try:
        # 테스터 초기화
        tester = MultimodalSystemTester()
        
        # 테스트 실행 (최대 3개 문서로 제한)
        results = tester.run_comprehensive_test(max_documents=3)
        
        # 결과 출력
        tester.print_summary()
        
        return results
        
    except Exception as e:
        print(f"테스트 실행 실패: {e}")
        logger.error(f"메인 테스트 실행 실패: {e}")
        return None


if __name__ == "__main__":
    main()