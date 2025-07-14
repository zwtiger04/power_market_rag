# 멀티스테이지 Docker 빌드
# Stage 1: 빌드 환경
FROM python:3.10-slim as builder

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치를 위한 디렉토리 생성
WORKDIR /app

# requirements.txt 복사 및 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: 런타임 환경
FROM python:3.10-slim as runtime

# 보안을 위한 non-root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 시스템 의존성 설치 (런타임에 필요한 것만)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 빌드 스테이지에서 설치된 Python 패키지 복사
COPY --from=builder /root/.local /home/appuser/.local

# 애플리케이션 코드 복사
COPY --chown=appuser:appuser . .

# Python path 설정
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app

# 로그 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

# 벡터 DB 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/vector_db && chown -R appuser:appuser /app/vector_db

# 사용자 전환
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "api.api_server:app", "--host", "0.0.0.0", "--port", "8000"]