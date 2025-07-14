"""
환경별 설정 관리 모듈
환경 변수와 설정 파일을 통합 관리합니다.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """환경 타입"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseSettings(BaseSettings):
    """데이터베이스 설정"""
    url: str = Field(..., env="DATABASE_URL")
    postgres_db: str = Field("power_market_rag", env="POSTGRES_DB")
    postgres_user: str = Field("postgres", env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    
    class Config:
        env_prefix = "DATABASE_"


class RedisSettings(BaseSettings):
    """Redis 설정"""
    url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    cache_ttl: int = Field(300, env="SEARCH_CACHE_TTL")
    
    class Config:
        env_prefix = "REDIS_"


class JWTSettings(BaseSettings):
    """JWT 토큰 설정"""
    secret_key: str = Field(..., env="JWT_SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    @validator("secret_key")
    def secret_key_must_be_strong(cls, v):
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v
    
    class Config:
        env_prefix = "JWT_"


class APISettings(BaseSettings):
    """API 서버 설정"""
    host: str = Field("0.0.0.0", env="API_HOST")
    port: int = Field(8000, env="API_PORT")
    prefix: str = Field("/api/v1", env="API_PREFIX")
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8000"], 
        env="CORS_ORIGINS"
    )
    
    class Config:
        env_prefix = "API_"


class VectorDBSettings(BaseSettings):
    """벡터 데이터베이스 설정"""
    path: str = Field("./vector_db", env="VECTOR_DB_PATH")
    type: str = Field("chromadb", env="VECTOR_DB_TYPE")
    collection_name: str = Field("power_market_docs", env="COLLECTION_NAME")
    
    class Config:
        env_prefix = "VECTOR_DB_"


class EmbeddingSettings(BaseSettings):
    """임베딩 모델 설정"""
    model: str = Field(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", 
        env="EMBEDDING_MODEL"
    )
    dimension: int = Field(384, env="EMBEDDING_DIMENSION")
    
    class Config:
        env_prefix = "EMBEDDING_"


class SearchSettings(BaseSettings):
    """검색 설정"""
    default_top_k: int = Field(5, env="DEFAULT_TOP_K")
    default_similarity_threshold: float = Field(0.7, env="DEFAULT_SIMILARITY_THRESHOLD")
    
    class Config:
        env_prefix = "SEARCH_"


class LoggingSettings(BaseSettings):
    """로깅 설정"""
    level: str = Field("INFO", env="LOG_LEVEL")
    file: str = Field("./logs/app.log", env="LOG_FILE")
    max_size: str = Field("10MB", env="LOG_MAX_SIZE")
    backup_count: int = Field(5, env="LOG_BACKUP_COUNT")
    
    class Config:
        env_prefix = "LOG_"


class SecuritySettings(BaseSettings):
    """보안 설정"""
    rate_limit_per_minute: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(1000, env="RATE_LIMIT_PER_HOUR")
    enable_api_key_auth: bool = Field(True, env="ENABLE_API_KEY_AUTH")
    admin_api_key: Optional[str] = Field(None, env="ADMIN_API_KEY")
    
    class Config:
        env_prefix = "SECURITY_"


class FileUploadSettings(BaseSettings):
    """파일 업로드 설정"""
    max_file_size: int = Field(50, env="MAX_FILE_SIZE")  # MB
    allowed_file_types: List[str] = Field(
        ["pdf", "docx", "txt", "md"], 
        env="ALLOWED_FILE_TYPES"
    )
    upload_dir: str = Field("./uploads", env="UPLOAD_DIR")
    
    class Config:
        env_prefix = "UPLOAD_"


class MonitoringSettings(BaseSettings):
    """모니터링 설정"""
    prometheus_port: int = Field(9090, env="PROMETHEUS_PORT")
    grafana_password: Optional[str] = Field(None, env="GRAFANA_PASSWORD")
    
    class Config:
        env_prefix = "MONITORING_"


class Settings(BaseSettings):
    """통합 설정 클래스"""
    
    # 환경 설정
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # 각 섹션별 설정
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    jwt: JWTSettings = JWTSettings()
    api: APISettings = APISettings()
    vector_db: VectorDBSettings = VectorDBSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    search: SearchSettings = SearchSettings()
    logging: LoggingSettings = LoggingSettings()
    security: SecuritySettings = SecuritySettings()
    file_upload: FileUploadSettings = FileUploadSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    
    @validator("environment", pre=True)
    def validate_environment(cls, v):
        if isinstance(v, str):
            return Environment(v.lower())
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        @classmethod
        def prepare_field(cls, field) -> None:
            if "env_names" in field.field_info.extra:
                return
            return {field.alias: os.environ.get(field.alias)}


def get_settings() -> Settings:
    """설정 인스턴스 반환 (싱글톤 패턴)"""
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()


# 환경별 설정 오버라이드
if settings.environment == Environment.DEVELOPMENT:
    settings.debug = True
    settings.logging.level = "DEBUG"
elif settings.environment == Environment.PRODUCTION:
    settings.debug = False
    settings.logging.level = "INFO"
    # 프로덕션 환경에서는 더 엄격한 보안 설정
    settings.security.rate_limit_per_minute = 30
    settings.security.enable_api_key_auth = True


def create_directories():
    """필요한 디렉토리 생성"""
    directories = [
        settings.logging.file.rsplit('/', 1)[0],  # 로그 디렉토리
        settings.vector_db.path,  # 벡터 DB 디렉토리
        settings.file_upload.upload_dir,  # 업로드 디렉토리
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


# 애플리케이션 시작 시 디렉토리 생성
create_directories()