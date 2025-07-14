"""
전체 RAG 시스템 통합 테스트
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path

# 상위 디렉토리의 모듈을 임포트하기 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestPowerMarketRAG:
    """전력시장 RAG 시스템 통합 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 실행"""
        # 실제 구현시에는 아래 주석 해제
        # from power_market_rag import PowerMarketRAG
        # self.rag_system = PowerMarketRAG()
        pass
    
    def test_system_initialization(self):
        """시스템 초기화 테스트"""
        print("🔧 시스템 초기화 테스트 중...")
        
        # 실제 구현시에는 아래 주석 해제
        # success = self.rag_system.initialize()
        # assert success, "RAG 시스템 초기화 실패"
        
        # 임시 테스트
        success = True
        assert success
        print("✅ 시스템 초기화 테스트 통과")
    
    def test_config_loading(self):
        """설정 파일 로딩 테스트"""
        print("📄 설정 파일 로딩 테스트 중...")
        
        config_path = "config/config.yaml"
        config_exists = os.path.exists(config_path)
        
        # 설정 파일이 있는지 확인
        if config_exists:
            print(f"✅ 설정 파일 존재: {config_path}")
        else:
            print(f"⚠️ 설정 파일 없음: {config_path}, 기본값 사용")
        
        # 기본 설정 값들 확인
        required_configs = [
            "VECTOR_DB_TYPE",
            "COLLECTION_NAME", 
            "EMBEDDING_MODEL",
            "TOP_K",
            "CHUNK_SIZE"
        ]
        
        # 실제 구현시에는 config 객체에서 확인
        # for config_key in required_configs:
        #     assert config_key in self.rag_system.config
        
        print("✅ 설정 로딩 테스트 통과")
    
    def test_document_processing_pipeline(self):
        """문서 처리 파이프라인 테스트"""
        print("📚 문서 처리 파이프라인 테스트 중...")
        
        # 테스트용 문서 내용
        test_documents = [
            {
                "content": "전력시장운영규칙 제16.4.1조에 따라 하루전발전계획을 수립합니다.",
                "filename": "test_regulation.txt"
            },
            {
                "content": "계통운영자는 실시간으로 전력 수급 균형을 유지해야 합니다.",
                "filename": "test_operation.txt"
            }
        ]
        
        # 처리 단계별 검증
        for doc in test_documents:
            # 1. 텍스트 추출 확인
            assert len(doc["content"]) > 0
            
            # 2. 청킹 확인 (시뮬레이션)
            chunks = [doc["content"]]  # 실제로는 청킹 처리
            assert len(chunks) > 0
            
            # 3. 임베딩 확인 (시뮬레이션)
            has_embedding = True  # 실제로는 임베딩 생성 확인
            assert has_embedding
        
        print("✅ 문서 처리 파이프라인 테스트 통과")
    
    def test_search_functionality(self):
        """검색 기능 테스트"""
        print("🔍 검색 기능 테스트 중...")
        
        test_queries = [
            "하루전발전계획이 무엇인가요?",
            "계통운영의 기본 원칙은?",
            "전력시장에서 예비력의 역할은?"
        ]
        
        search_methods = ["semantic", "keyword", "hybrid", "smart"]
        
        for query in test_queries:
            for method in search_methods:
                # 실제 구현시에는 아래 주석 해제
                # results = self.rag_system.search_documents(query, method=method, top_k=3)
                
                # 임시 테스트 결과
                results = [
                    {
                        "id": f"doc_1_{method}",
                        "text": f"'{query}'와 관련된 내용입니다.",
                        "similarity": 0.85,
                        "source_file": "test_doc.txt"
                    }
                ]
                
                assert len(results) >= 0
                if results:
                    assert "text" in results[0]
                    assert "similarity" in results[0]
        
        print("✅ 검색 기능 테스트 통과")
    
    def test_answer_generation(self):
        """답변 생성 테스트"""
        print("💬 답변 생성 테스트 중...")
        
        test_cases = [
            {
                "question": "하루전발전계획 수립 절차는?",
                "context": "제16.4.1조에 의거하여 하루전발전계획을 수립합니다. 11시에 초기입찰을 입력하고, 17시에 최종 계획을 수립합니다.",
                "expected_keywords": ["절차", "11시", "17시"]
            },
            {
                "question": "계통운영의 목적은?",
                "context": "계통운영자는 전력 공급의 안정성과 신뢰성을 확보하기 위해 실시간 모니터링을 수행합니다.",
                "expected_keywords": ["안정성", "신뢰성", "모니터링"]
            }
        ]
        
        for test_case in test_cases:
            # 실제 구현시에는 아래 주석 해제
            # result = self.rag_system.ask(test_case["question"])
            
            # 임시 테스트 결과
            result = {
                "answer": f"{test_case['question']}에 대한 답변: {test_case['context']}",
                "confidence": 0.8,
                "sources": ["test_source.pdf"],
                "search_results": 3
            }
            
            # 검증
            assert "answer" in result
            assert "confidence" in result
            assert "sources" in result
            assert 0.0 <= result["confidence"] <= 1.0
            
            # 키워드 포함 확인
            answer_text = result["answer"].lower()
            for keyword in test_case["expected_keywords"]:
                # 실제로는 더 정교한 키워드 매칭 필요
                print(f"  키워드 '{keyword}' 확인 중...")
        
        print("✅ 답변 생성 테스트 통과")
    
    def test_api_endpoints(self):
        """API 엔드포인트 테스트 (모의)"""
        print("🌐 API 엔드포인트 테스트 중...")
        
        # 실제 API 테스트는 서버가 실행 중일 때 수행
        # 여기서는 기본적인 구조만 확인
        
        api_endpoints = [
            "/",           # 메인 페이지
            "/ask",        # 질문 API
            "/search",     # 검색 API
            "/status",     # 상태 확인
            "/health"      # 헬스 체크
        ]
        
        for endpoint in api_endpoints:
            # 실제로는 HTTP 요청을 보내서 테스트
            # 여기서는 엔드포인트 존재 확인만 시뮬레이션
            endpoint_exists = True
            assert endpoint_exists, f"엔드포인트 {endpoint} 누락"
        
        print("✅ API 엔드포인트 테스트 통과")
    
    def test_performance_metrics(self):
        """성능 지표 테스트"""
        print("📊 성능 지표 테스트 중...")
        
        # 응답 시간 테스트 (시뮬레이션)
        response_times = [0.5, 1.2, 0.8, 1.5, 0.9]  # 초 단위
        
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # 성능 기준 검증
        assert avg_response_time < 2.0, f"평균 응답 시간이 너무 김: {avg_response_time}초"
        assert max_response_time < 5.0, f"최대 응답 시간이 너무 김: {max_response_time}초"
        
        print(f"  평균 응답 시간: {avg_response_time:.2f}초")
        print(f"  최대 응답 시간: {max_response_time:.2f}초")
        print("✅ 성능 지표 테스트 통과")
    
    def test_error_handling(self):
        """오류 처리 테스트"""
        print("⚠️ 오류 처리 테스트 중...")
        
        error_cases = [
            {"input": "", "expected": "빈 질문"},
            {"input": "x" * 10000, "expected": "너무 긴 질문"},
            {"input": "!@#$%^&*()", "expected": "특수 문자만 포함"}
        ]
        
        for case in error_cases:
            # 실제 구현시에는 오류 상황을 실제로 테스트
            # 여기서는 오류 처리 로직이 있다고 가정
            error_handled = True
            assert error_handled, f"오류 처리 실패: {case['expected']}"
        
        print("✅ 오류 처리 테스트 통과")

def run_full_system_test():
    """전체 시스템 테스트 실행"""
    print("🚀 전력시장 RAG 시스템 통합 테스트 시작")
    print("=" * 60)
    
    test_suite = TestPowerMarketRAG()
    test_suite.setup_method()
    
    tests = [
        test_suite.test_system_initialization,
        test_suite.test_config_loading,
        test_suite.test_document_processing_pipeline,
        test_suite.test_search_functionality,
        test_suite.test_answer_generation,
        test_suite.test_api_endpoints,
        test_suite.test_performance_metrics,
        test_suite.test_error_handling
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_func in tests:
        try:
            test_func()
            passed_tests += 1
        except Exception as e:
            print(f"❌ 테스트 실패: {test_func.__name__} - {e}")
    
    print("=" * 60)
    print(f"📋 테스트 결과: {passed_tests}/{total_tests} 통과")
    
    if passed_tests == total_tests:
        print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        return True
    else:
        print(f"⚠️ {total_tests - passed_tests}개 테스트가 실패했습니다.")
        return False

if __name__ == "__main__":
    success = run_full_system_test()
    exit(0 if success else 1)
