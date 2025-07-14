"""
API 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthCheck:
    """헬스 체크 테스트"""
    
    def test_health_check(self, test_client: TestClient):
        """기본 헬스 체크"""
        response = test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_health_detailed(self, test_client: TestClient):
        """상세 헬스 체크"""
        response = test_client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert "database" in data["services"]
        assert "redis" in data["services"]
        assert "vector_store" in data["services"]


class TestAuthenticationAPI:
    """인증 API 테스트"""
    
    def test_register_user(self, test_client: TestClient, test_user_data):
        """사용자 등록 테스트"""
        response = test_client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "password" not in data  # 비밀번호는 응답에 포함되지 않아야 함
    
    def test_register_duplicate_user(self, test_client: TestClient, test_user_data):
        """중복 사용자 등록 테스트"""
        # 첫 번째 등록
        response = test_client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 201
        
        # 중복 등록 시도
        response = test_client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_login_valid_user(self, test_client: TestClient, test_user_data):
        """유효한 사용자 로그인"""
        # 사용자 등록
        test_client.post("/api/v1/auth/register", json=test_user_data)
        
        # 로그인
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        response = test_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, test_client: TestClient):
        """잘못된 인증 정보로 로그인"""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        response = test_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_get_user_profile(self, test_client: TestClient, authenticated_user):
        """사용자 프로필 조회"""
        response = test_client.get(
            "/api/v1/auth/me", 
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["username"] == authenticated_user["user_data"]["username"]
        assert data["email"] == authenticated_user["user_data"]["email"]
    
    def test_refresh_token(self, test_client: TestClient, authenticated_user):
        """토큰 갱신 테스트"""
        # 기존 토큰으로 갱신 요청
        response = test_client.post(
            "/api/v1/auth/refresh",
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


class TestDocumentAPI:
    """문서 API 테스트"""
    
    def test_upload_document(self, test_client: TestClient, authenticated_user, sample_pdf_file):
        """문서 업로드 테스트"""
        with open(sample_pdf_file, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            response = test_client.post(
                "/api/v1/documents/upload",
                files=files,
                headers=authenticated_user["headers"]
            )
        
        assert response.status_code == 201
        data = response.json()
        assert "document_id" in data
        assert data["filename"] == "test.pdf"
        assert data["status"] == "uploaded"
    
    def test_upload_invalid_file_type(self, test_client: TestClient, authenticated_user):
        """잘못된 파일 형식 업로드"""
        files = {"file": ("test.txt", b"invalid content", "text/plain")}
        response = test_client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 400
        assert "File type not supported" in response.json()["detail"]
    
    def test_list_documents(self, test_client: TestClient, authenticated_user):
        """문서 목록 조회"""
        response = test_client.get(
            "/api/v1/documents/",
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "documents" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
    
    def test_delete_document(self, test_client: TestClient, authenticated_user, sample_pdf_file):
        """문서 삭제 테스트"""
        # 먼저 문서 업로드
        with open(sample_pdf_file, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            upload_response = test_client.post(
                "/api/v1/documents/upload",
                files=files,
                headers=authenticated_user["headers"]
            )
        
        document_id = upload_response.json()["document_id"]
        
        # 문서 삭제
        response = test_client.delete(
            f"/api/v1/documents/{document_id}",
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Document deleted successfully"


class TestSearchAPI:
    """검색 API 테스트"""
    
    def test_search_documents(self, test_client: TestClient, authenticated_user, test_query_data):
        """문서 검색 테스트"""
        response = test_client.post(
            "/api/v1/search/",
            json=test_query_data,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert "total_results" in data
        assert "search_time" in data
    
    def test_search_with_filters(self, test_client: TestClient, authenticated_user):
        """필터가 포함된 검색"""
        search_data = {
            "query": "전력시장 운영",
            "filters": {
                "category": "regulation",
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2024-12-31"
                }
            },
            "top_k": 10
        }
        
        response = test_client.post(
            "/api/v1/search/",
            json=search_data,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert len(data["results"]) <= 10
    
    def test_search_invalid_query(self, test_client: TestClient, authenticated_user):
        """잘못된 쿼리 테스트"""
        invalid_query = {"query": ""}  # 빈 쿼리
        
        response = test_client.post(
            "/api/v1/search/",
            json=invalid_query,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 400
        assert "Query cannot be empty" in response.json()["detail"]


class TestRAGAPI:
    """RAG API 테스트"""
    
    def test_ask_question(self, test_client: TestClient, authenticated_user):
        """질문 답변 테스트"""
        question_data = {
            "question": "전력시장 운영 규칙에 대해 설명해주세요.",
            "context_limit": 5,
            "temperature": 0.7
        }
        
        response = test_client.post(
            "/api/v1/rag/ask",
            json=question_data,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "confidence" in data
        assert "response_time" in data
    
    def test_ask_with_conversation_history(self, test_client: TestClient, authenticated_user):
        """대화 히스토리가 포함된 질문"""
        question_data = {
            "question": "그럼 구체적인 절차는 어떻게 되나요?",
            "conversation_history": [
                {
                    "role": "user",
                    "content": "전력시장 운영 규칙은 무엇인가요?"
                },
                {
                    "role": "assistant", 
                    "content": "전력시장 운영 규칙은 전력시장의 효율적 운영을 위한 규정입니다."
                }
            ]
        }
        
        response = test_client.post(
            "/api/v1/rag/ask",
            json=question_data,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "answer" in data
        assert "sources" in data


class TestMonitoringAPI:
    """모니터링 API 테스트"""
    
    def test_prometheus_metrics(self, test_client: TestClient):
        """Prometheus 메트릭 엔드포인트"""
        response = test_client.get("/monitoring/api/prometheus")
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        assert "rag_api_requests_total" in content
        assert "rag_system_cpu_usage_percent" in content
    
    def test_dashboard_data(self, test_client: TestClient):
        """대시보드 데이터 API"""
        response = test_client.get("/monitoring/api/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        assert "overview" in data
        assert "charts" in data
        assert "alerts" in data
    
    def test_alert_statistics(self, test_client: TestClient):
        """알림 통계 API"""
        response = test_client.get("/monitoring/api/alerts")
        assert response.status_code == 200
        
        data = response.json()
        assert "active_rules" in data
        assert "total_rules" in data
        assert "recent_alerts" in data


class TestCacheAPI:
    """캐시 API 테스트"""
    
    def test_cache_stats(self, test_client: TestClient, authenticated_user):
        """캐시 통계 조회"""
        response = test_client.get(
            "/api/v1/cache/stats",
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "hit_rate" in data
        assert "total_operations" in data
        assert "memory_usage" in data
    
    def test_cache_clear(self, test_client: TestClient, authenticated_user):
        """캐시 클리어"""
        response = test_client.delete(
            "/api/v1/cache/clear",
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Cache cleared successfully"


@pytest.mark.slow
class TestPerformance:
    """성능 테스트"""
    
    def test_search_performance(self, test_client: TestClient, authenticated_user, performance_monitor):
        """검색 성능 테스트"""
        query_data = {"query": "전력시장 운영 규칙", "top_k": 10}
        
        performance_monitor.start()
        response = test_client.post(
            "/api/v1/search/",
            json=query_data,
            headers=authenticated_user["headers"]
        )
        duration = performance_monitor.stop("search")
        
        assert response.status_code == 200
        assert duration < 2.0  # 2초 이내 응답
    
    def test_concurrent_requests(self, test_client: TestClient, authenticated_user):
        """동시 요청 처리 테스트"""
        import concurrent.futures
        import threading
        
        def make_request():
            return test_client.get(
                "/health",
                headers=authenticated_user["headers"]
            )
        
        # 10개의 동시 요청
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in futures]
        
        # 모든 요청이 성공해야 함
        for response in results:
            assert response.status_code == 200


@pytest.mark.integration
class TestIntegration:
    """통합 테스트"""
    
    def test_full_workflow(self, test_client: TestClient, authenticated_user, sample_pdf_file):
        """전체 워크플로우 테스트"""
        # 1. 문서 업로드
        with open(sample_pdf_file, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            upload_response = test_client.post(
                "/api/v1/documents/upload",
                files=files,
                headers=authenticated_user["headers"]
            )
        assert upload_response.status_code == 201
        
        # 2. 문서 검색
        search_response = test_client.post(
            "/api/v1/search/",
            json={"query": "test content", "top_k": 5},
            headers=authenticated_user["headers"]
        )
        assert search_response.status_code == 200
        
        # 3. RAG 질문
        ask_response = test_client.post(
            "/api/v1/rag/ask",
            json={"question": "이 문서는 무엇에 관한 내용인가요?"},
            headers=authenticated_user["headers"]
        )
        assert ask_response.status_code == 200
        
        # 4. 문서 삭제
        document_id = upload_response.json()["document_id"]
        delete_response = test_client.delete(
            f"/api/v1/documents/{document_id}",
            headers=authenticated_user["headers"]
        )
        assert delete_response.status_code == 200