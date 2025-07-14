"""
pytest 설정 및 공통 픽스처
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 테스트용 환경 변수 설정
os.environ.update({
    "ENVIRONMENT": "testing",
    "DATABASE_URL": "sqlite:///./test.db",
    "REDIS_URL": "redis://localhost:6379/15",  # 테스트용 DB
    "JWT_SECRET_KEY": "test-secret-key-for-testing-only",
    "LOG_LEVEL": "DEBUG",
})

from api.api_server import app
from database.connection import get_database_connection
from database.models import Base, create_tables
from cache.redis_client import get_redis_client
from monitoring import get_logger, setup_logging


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """세션 범위 이벤트 루프"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def setup_test_logging():
    """테스트용 로깅 설정"""
    with tempfile.TemporaryDirectory() as temp_dir:
        setup_logging(
            level="DEBUG",
            log_dir=temp_dir,
            app_name="test_power_market_rag",
            environment="testing"
        )
        yield
        

@pytest.fixture(scope="session")
def test_db_engine():
    """테스트용 데이터베이스 엔진"""
    engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False}
    )
    
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # 테스트 후 정리
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture
def test_db_session(test_db_engine):
    """테스트용 데이터베이스 세션"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=test_db_engine
    )
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
async def test_redis_client():
    """테스트용 Redis 클라이언트"""
    redis_client = get_redis_client()
    await redis_client.connect()
    
    # 테스트 시작 전 테스트 DB 클리어
    await redis_client.flushdb()
    
    yield redis_client
    
    # 테스트 후 정리
    await redis_client.flushdb()
    await redis_client.disconnect()


@pytest.fixture
def test_client() -> TestClient:
    """테스트용 FastAPI 클라이언트"""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """테스트용 사용자 데이터"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def test_admin_data():
    """테스트용 관리자 데이터"""
    return {
        "username": "admin",
        "email": "admin@example.com", 
        "password": "adminpassword123",
        "full_name": "Admin User",
        "is_admin": True
    }


@pytest.fixture
def test_document_data():
    """테스트용 문서 데이터"""
    return {
        "title": "테스트 문서",
        "content": "이것은 테스트용 문서 내용입니다. 전력시장 운영에 관한 내용을 포함합니다.",
        "metadata": {
            "source": "test_document.pdf",
            "page": 1,
            "category": "test"
        }
    }


@pytest.fixture
def test_query_data():
    """테스트용 쿼리 데이터"""
    return {
        "query": "전력시장 운영 규칙은 무엇인가요?",
        "top_k": 5,
        "similarity_threshold": 0.7
    }


@pytest.fixture
def mock_vector_store(monkeypatch):
    """Mock 벡터 스토어"""
    class MockVectorStore:
        def __init__(self):
            self.documents = []
        
        def add_documents(self, documents):
            self.documents.extend(documents)
            return [f"doc_{i}" for i in range(len(documents))]
        
        def similarity_search(self, query, k=5, score_threshold=0.0):
            # 간단한 Mock 검색 결과
            return [
                {
                    "content": "전력시장 운영 규칙 관련 내용",
                    "metadata": {"source": "test.pdf", "page": 1},
                    "score": 0.9
                }
            ]
        
        def delete_collection(self):
            self.documents.clear()
    
    mock_store = MockVectorStore()
    monkeypatch.setattr("vector_db.vector_store.VectorStore", lambda: mock_store)
    return mock_store


@pytest.fixture
def mock_embedding_model(monkeypatch):
    """Mock 임베딩 모델"""
    class MockEmbeddingModel:
        def encode(self, texts):
            # 더미 임베딩 벡터 반환
            if isinstance(texts, str):
                return [0.1] * 384
            return [[0.1] * 384 for _ in texts]
    
    mock_model = MockEmbeddingModel()
    monkeypatch.setattr(
        "embeddings.text_embedder.SentenceTransformer", 
        lambda model_name: mock_model
    )
    return mock_model


@pytest.fixture
def temp_upload_dir():
    """임시 업로드 디렉토리"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_pdf_file():
    """샘플 PDF 파일"""
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000079 00000 n \n0000000136 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n212\n%%EOF"
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(content)
        f.flush()
        yield f.name
    
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
async def authenticated_user(test_client, test_user_data):
    """인증된 사용자"""
    # 사용자 등록
    response = test_client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    
    # 로그인
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    }
    response = test_client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    
    token_data = response.json()
    return {
        "token": token_data["access_token"],
        "headers": {"Authorization": f"Bearer {token_data['access_token']}"},
        "user_data": test_user_data
    }


@pytest.fixture
def performance_monitor():
    """성능 모니터링"""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.measurements = []
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self, operation_name="operation"):
            if self.start_time:
                duration = time.time() - self.start_time
                self.measurements.append({
                    "operation": operation_name,
                    "duration": duration
                })
                self.start_time = None
                return duration
        
        def get_stats(self):
            if not self.measurements:
                return {}
            
            durations = [m["duration"] for m in self.measurements]
            return {
                "count": len(durations),
                "total": sum(durations),
                "average": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations)
            }
    
    return PerformanceMonitor()


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """테스트 후 파일 정리"""
    yield
    
    # 테스트 파일들 정리
    test_files = [
        "./test.db",
        "./test.db-journal",
        "./test_vector_db",
        "./test_logs"
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                import shutil
                shutil.rmtree(file_path)


# Pytest 설정
def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )


def pytest_collection_modifyitems(config, items):
    """테스트 아이템 수정"""
    for item in items:
        # 파일 경로에 따른 자동 마커 추가
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # 비동기 테스트 마커 추가
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)