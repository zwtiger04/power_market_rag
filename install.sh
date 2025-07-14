#!/bin/bash

# 전력시장 RAG 시스템 설치 스크립트
# Ubuntu/WSL 환경에서 실행

echo "🚀 전력시장 RAG 시스템 설치를 시작합니다..."

# 1. Python 버전 확인
echo "1. Python 버전 확인 중..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python3가 설치되어 있지 않습니다. Python3를 먼저 설치해주세요."
    exit 1
fi

# 2. 가상환경 생성
echo "2. Python 가상환경 생성 중..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ 가상환경 생성 실패. python3-venv를 설치해주세요:"
    echo "sudo apt update && sudo apt install python3-venv"
    exit 1
fi

# 3. 가상환경 활성화
echo "3. 가상환경 활성화 중..."
source venv/bin/activate

# 4. pip 업그레이드
echo "4. pip 업그레이드 중..."
pip install --upgrade pip

# 5. 필요한 패키지 설치
echo "5. 필요한 패키지 설치 중..."
echo "⏳ 이 과정은 몇 분 정도 소요될 수 있습니다..."

pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 패키지 설치 실패. 네트워크 연결을 확인해주세요."
    exit 1
fi

# 6. 필요한 디렉토리 생성
echo "6. 필요한 디렉토리 확인 중..."
mkdir -p logs
mkdir -p documents

# 7. 설치 완료 메시지
echo ""
echo "✅ 전력시장 RAG 시스템 설치가 완료되었습니다!"
echo ""
echo "📝 다음 명령어로 시스템을 실행할 수 있습니다:"
echo ""
echo "   # 가상환경 활성화"
echo "   source venv/bin/activate"
echo ""
echo "   # 메인 시스템 실행"
echo "   python power_market_rag.py"
echo ""
echo "   # API 서버 실행"
echo "   python api/api_server.py"
echo ""
echo "📚 문서를 documents/ 폴더에 넣고 시스템을 실행하세요."
echo ""
echo "🌐 API 서버를 실행하면 http://localhost:8000 에서 웹 인터페이스를 사용할 수 있습니다."
