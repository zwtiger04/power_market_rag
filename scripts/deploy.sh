#!/bin/bash

# 전력시장 RAG 시스템 배포 스크립트
# 사용법: ./scripts/deploy.sh [environment] [version]
# 예시: ./scripts/deploy.sh production v1.0.0

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 스크립트 시작
log_info "🚀 전력시장 RAG 시스템 배포 시작"

# 기본 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
COMPOSE_FILE="docker-compose.yml"

# 환경에 따른 설정
case $ENVIRONMENT in
    "production")
        COMPOSE_FILE="docker-compose.yml"
        APP_PORT=8000
        ;;
    "staging")
        COMPOSE_FILE="docker-compose.dev.yml"
        APP_PORT=8001
        ;;
    "development")
        COMPOSE_FILE="docker-compose.dev.yml"
        APP_PORT=8002
        ;;
    *)
        log_error "지원하지 않는 환경: $ENVIRONMENT"
        log_info "지원 환경: production, staging, development"
        exit 1
        ;;
esac

log_info "배포 환경: $ENVIRONMENT"
log_info "버전: $VERSION"
log_info "Compose 파일: $COMPOSE_FILE"

# 필수 파일 확인
check_prerequisites() {
    log_info "📋 배포 전 요구사항 확인"
    
    local missing_files=()
    local required_files=(
        "$PROJECT_ROOT/$COMPOSE_FILE"
        "$PROJECT_ROOT/.env.example"
        "$PROJECT_ROOT/Dockerfile"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log_error "필수 파일이 누락되었습니다:"
        printf '%s\n' "${missing_files[@]}"
        exit 1
    fi
    
    # Docker 및 Docker Compose 확인
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되어 있지 않습니다"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose가 설치되어 있지 않습니다"
        exit 1
    fi
    
    log_success "모든 요구사항이 충족되었습니다"
}

# 환경 변수 설정
setup_environment() {
    log_info "🔧 환경 변수 설정"
    
    cd "$PROJECT_ROOT"
    
    if [[ ! -f ".env" ]]; then
        log_warning ".env 파일이 없습니다. .env.example을 복사합니다."
        cp .env.example .env
        log_warning "배포 전에 .env 파일의 설정을 확인하고 수정하세요."
        
        if [[ "$ENVIRONMENT" == "production" ]]; then
            log_error "프로덕션 환경에서는 .env 파일을 수동으로 설정해야 합니다"
            exit 1
        fi
    fi
    
    # 환경별 설정 업데이트
    case $ENVIRONMENT in
        "production")
            sed -i.bak "s/ENVIRONMENT=.*/ENVIRONMENT=production/" .env
            sed -i.bak "s/API_PORT=.*/API_PORT=$APP_PORT/" .env
            ;;
        "staging")
            sed -i.bak "s/ENVIRONMENT=.*/ENVIRONMENT=staging/" .env
            sed -i.bak "s/API_PORT=.*/API_PORT=$APP_PORT/" .env
            ;;
        "development")
            sed -i.bak "s/ENVIRONMENT=.*/ENVIRONMENT=development/" .env
            sed -i.bak "s/API_PORT=.*/API_PORT=$APP_PORT/" .env
            ;;
    esac
    
    log_success "환경 변수 설정 완료"
}

# 기존 서비스 중지
stop_services() {
    log_info "🛑 기존 서비스 중지"
    
    cd "$PROJECT_ROOT"
    
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        docker-compose -f "$COMPOSE_FILE" down
        log_success "기존 서비스가 중지되었습니다"
    else
        log_info "실행 중인 서비스가 없습니다"
    fi
}

# 백업 생성
create_backup() {
    log_info "💾 데이터베이스 백업 생성"
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        local backup_dir="$PROJECT_ROOT/backups"
        local backup_file="$backup_dir/backup_$(date +%Y%m%d_%H%M%S).sql"
        
        mkdir -p "$backup_dir"
        
        # PostgreSQL 백업 (컨테이너가 실행 중인 경우)
        if docker-compose -f "$COMPOSE_FILE" ps postgres | grep -q "Up"; then
            docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U postgres power_market_rag > "$backup_file"
            log_success "데이터베이스 백업 생성: $backup_file"
        else
            log_warning "PostgreSQL 컨테이너가 실행되지 않아 백업을 생략합니다"
        fi
    else
        log_info "개발/스테이징 환경에서는 백업을 생략합니다"
    fi
}

# 이미지 빌드
build_images() {
    log_info "🔨 Docker 이미지 빌드"
    
    cd "$PROJECT_ROOT"
    
    # 이미지 빌드
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    # 이미지 태깅
    if [[ "$VERSION" != "latest" ]]; then
        docker tag power-market-rag:latest "power-market-rag:$VERSION"
    fi
    
    log_success "Docker 이미지 빌드 완료"
}

# 데이터베이스 마이그레이션
run_migrations() {
    log_info "📦 데이터베이스 마이그레이션 실행"
    
    cd "$PROJECT_ROOT"
    
    # PostgreSQL과 Redis 시작
    docker-compose -f "$COMPOSE_FILE" up -d postgres redis
    
    # 데이터베이스 연결 대기
    log_info "데이터베이스 연결 대기..."
    sleep 10
    
    # 마이그레이션 실행
    docker-compose -f "$COMPOSE_FILE" run --rm app python -c "
from database.connection import get_database_connection
from database.models import create_tables
create_tables()
print('데이터베이스 테이블 생성 완료')
"
    
    log_success "데이터베이스 마이그레이션 완료"
}

# 서비스 시작
start_services() {
    log_info "🚀 서비스 시작"
    
    cd "$PROJECT_ROOT"
    
    # 모든 서비스 시작
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_info "서비스 시작 대기..."
    sleep 15
    
    log_success "모든 서비스가 시작되었습니다"
}

# 헬스 체크
health_check() {
    log_info "🏥 헬스 체크 실행"
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s -f "http://localhost:$APP_PORT/health" > /dev/null; then
            log_success "애플리케이션이 정상적으로 실행되고 있습니다"
            return 0
        fi
        
        log_info "헬스 체크 시도 $attempt/$max_attempts..."
        sleep 5
        ((attempt++))
    done
    
    log_error "헬스 체크 실패: 애플리케이션이 응답하지 않습니다"
    return 1
}

# 배포 후 테스트
post_deploy_tests() {
    log_info "🧪 배포 후 테스트 실행"
    
    cd "$PROJECT_ROOT"
    
    # 기본 API 테스트
    local api_url="http://localhost:$APP_PORT"
    
    # 헬스 체크
    if ! curl -s -f "$api_url/health" > /dev/null; then
        log_error "헬스 체크 API 실패"
        return 1
    fi
    
    # 메트릭 엔드포인트 확인
    if ! curl -s -f "$api_url/monitoring/api/prometheus" > /dev/null; then
        log_warning "메트릭 엔드포인트에 접근할 수 없습니다"
    fi
    
    log_success "배포 후 테스트 완료"
}

# 서비스 상태 출력
show_status() {
    log_info "📊 서비스 상태"
    
    cd "$PROJECT_ROOT"
    
    echo ""
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    
    log_info "📱 접속 정보:"
    echo "  • API 서버: http://localhost:$APP_PORT"
    echo "  • API 문서: http://localhost:$APP_PORT/docs"
    echo "  • 헬스 체크: http://localhost:$APP_PORT/health"
    echo "  • 모니터링: http://localhost:$APP_PORT/monitoring"
    echo ""
    
    log_info "📝 로그 확인:"
    echo "  docker-compose -f $COMPOSE_FILE logs -f app"
    echo ""
}

# 롤백 함수
rollback() {
    log_warning "🔄 롤백 실행"
    
    cd "$PROJECT_ROOT"
    
    # 현재 서비스 중지
    docker-compose -f "$COMPOSE_FILE" down
    
    # 이전 이미지로 롤백 (latest가 아닌 경우)
    if [[ "$VERSION" != "latest" ]]; then
        docker tag power-market-rag:latest "power-market-rag:rollback-$VERSION"
        docker tag power-market-rag:latest power-market-rag:latest
    fi
    
    # 서비스 재시작
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_warning "롤백이 완료되었습니다"
}

# 정리 함수
cleanup() {
    log_info "🧹 정리 작업"
    
    # 사용하지 않는 이미지 제거
    docker image prune -f
    
    # 사용하지 않는 볼륨 제거 (주의: 데이터 손실 가능)
    if [[ "$ENVIRONMENT" != "production" ]]; then
        docker volume prune -f
    fi
    
    log_success "정리 작업 완료"
}

# 메인 배포 프로세스
main() {
    # 트랩 설정 (오류 발생 시 롤백)
    trap 'log_error "배포 중 오류 발생"; rollback; exit 1' ERR
    
    check_prerequisites
    setup_environment
    
    # 프로덕션 환경에서만 백업 생성
    if [[ "$ENVIRONMENT" == "production" ]]; then
        create_backup
    fi
    
    stop_services
    build_images
    run_migrations
    start_services
    
    if health_check; then
        post_deploy_tests
        show_status
        cleanup
        
        log_success "🎉 배포가 성공적으로 완료되었습니다!"
    else
        log_error "헬스 체크 실패로 인한 롤백 실행"
        rollback
        exit 1
    fi
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi