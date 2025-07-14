#!/bin/bash

# Enhanced 전력시장 RAG 시스템 실행 스크립트

echo "🚀 Enhanced 전력시장 RAG 시스템"
echo "=================================="

# Python 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "📦 가상환경 활성화 중..."
    source venv/bin/activate
fi

# 메뉴 선택
echo ""
echo "실행할 작업을 선택하세요:"
echo "1. 시스템 재구축 (첫 실행 또는 업그레이드)"
echo "2. Enhanced RAG 시스템 실행"
echo "3. 시스템 상태 확인"
echo "4. 도메인별 개요 보기"
echo "5. 종료"
echo ""

read -p "선택 (1-5): " choice

case $choice in
    1)
        echo "🔧 시스템 재구축을 시작합니다..."
        python rebuild_enhanced_system.py --documents documents --force
        ;;
    2)
        echo "⚡ Enhanced RAG 시스템을 실행합니다..."
        python power_market_rag_enhanced.py
        ;;
    3)
        echo "📊 시스템 상태를 확인합니다..."
        python -c "
from power_market_rag_enhanced import EnhancedPowerMarketRAG
import json

rag = EnhancedPowerMarketRAG()
if rag.initialize():
    status = rag.get_enhanced_system_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
else:
    print('시스템 초기화 실패')
"
        ;;
    4)
        echo "📋 도메인별 개요를 확인합니다..."
        echo "도메인 선택:"
        echo "1. 발전계획"
        echo "2. 계통운영" 
        echo "3. 전력거래"
        echo "4. 시장운영"
        echo "5. 예비력"
        echo "6. 송전제약"
        
        read -p "도메인 선택 (1-6): " domain_choice
        
        case $domain_choice in
            1) domain="발전계획" ;;
            2) domain="계통운영" ;;
            3) domain="전력거래" ;;
            4) domain="시장운영" ;;
            5) domain="예비력" ;;
            6) domain="송전제약" ;;
            *) domain="발전계획" ;;
        esac
        
        python -c "
from power_market_rag_enhanced import EnhancedPowerMarketRAG
import json

rag = EnhancedPowerMarketRAG()
if rag.initialize():
    overview = rag.get_domain_overview('$domain')
    print(json.dumps(overview, ensure_ascii=False, indent=2))
else:
    print('시스템 초기화 실패')
"
        ;;
    5)
        echo "👋 Enhanced RAG 시스템을 종료합니다."
        exit 0
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        exit 1
        ;;
esac

echo ""
echo "✅ 작업이 완료되었습니다!"