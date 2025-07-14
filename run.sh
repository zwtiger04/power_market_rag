#!/bin/bash

# 전력시장 RAG 시스템 실행 스크립트

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수: 제목 출력
print_title() {
    echo -e "${BLUE}"
    echo "=================================================="
    echo "         ⚡ 전력시장 RAG 시스템 실행기 ⚡"
    echo "=================================================="
    echo -e "${NC}"
}

# 함수: 가상환경 확인 및 활성화
activate_venv() {
    if [ -d "venv" ]; then
        echo -e "${GREEN}📦 가상환경 활성화 중...${NC}"
        source venv/bin/activate
        echo -e "${GREEN}✅ 가상환경이 활성화되었습니다.${NC}"
    else
        echo -e "${RED}❌ 가상환경이 없습니다. 먼저 install.sh를 실행해주세요.${NC}"
        exit 1
    fi
}

# 함수: API 서버 실행
run_api_server() {
    echo -e "${YELLOW}🌐 API 서버를 시작합니다...${NC}"
    echo -e "${BLUE}📍 웹 인터페이스: http://localhost:8000${NC}"
    echo -e "${BLUE}📖 API 문서: http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  서버를 중지하려면 Ctrl+C를 누르세요.${NC}"
    echo ""
    
    cd api
    python api_server.py
}

# 함수: 메인 시스템 실행
run_main_system() {
    echo -e "${YELLOW}🔄 메인 RAG 시스템을 시작합니다...${NC}"
    python power_market_rag.py
}

# 함수: 테스트 실행
run_tests() {
    echo -e "${YELLOW}🧪 시스템 테스트를 실행합니다...${NC}"
    python -m pytest tests/ -v
}

# 메인 함수
main() {
    print_title
    
    # 현재 디렉토리 확인
    if [ ! -f "power_market_rag.py" ]; then
        echo -e "${RED}❌ power_market_rag.py 파일을 찾을 수 없습니다.${NC}"
        echo -e "${RED}   올바른 프로젝트 디렉토리에서 실행해주세요.${NC}"
        exit 1
    fi
    
    # 가상환경 활성화
    activate_venv
    
    # 실행 모드 선택
    echo -e "${BLUE}실행할 모드를 선택하세요:${NC}"
    echo "1) 🌐 API 서버 실행 (웹 인터페이스 포함)"
    echo "2) 🔄 메인 시스템 실행 (콘솔 모드)"
    echo "3) 🧪 시스템 테스트 실행"
    echo "4) 📊 시스템 상태 확인"
    echo "5) 🚪 종료"
    echo ""
    
    read -p "선택 (1-5): " choice
    
    case $choice in
        1)
            run_api_server
            ;;
        2)
            run_main_system
            ;;
        3)
            run_tests
            ;;
        4)
            echo -e "${YELLOW}📊 시스템 상태를 확인합니다...${NC}"
            python -c "
from power_market_rag import PowerMarketRAG
rag = PowerMarketRAG()
status = rag.get_system_status()
print(f'시스템 상태: {status}')
            "
            ;;
        5)
            echo -e "${GREEN}👋 시스템을 종료합니다.${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ 잘못된 선택입니다. 1-5 중에서 선택해주세요.${NC}"
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
