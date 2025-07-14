#!/usr/bin/env python3
"""
전력시장운영규칙 문서 로딩 스크립트
- documents 폴더와 PowerMarketRules 폴더 모두 처리
- PDF 파일들을 RAG 시스템에 로드
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_power_market_documents():
    """전력시장 문서들을 RAG 시스템에 로드"""
    print("⚡ 전력시장운영규칙 문서 로딩을 시작합니다...")
    
    # 문서 폴더들
    document_folders = [
        "documents",
        "PowerMarketRules"
    ]
    
    # 지원 파일 형식
    supported_extensions = ['.pdf', '.txt', '.md', '.docx']
    
    total_files = 0
    
    for folder in document_folders:
        folder_path = Path(folder)
        if folder_path.exists():
            files = []
            for ext in supported_extensions:
                files.extend(list(folder_path.glob(f"*{ext}")))
            
            print(f"📂 {folder} 폴더: {len(files)}개 파일 발견")
            for file in files[:5]:  # 처음 5개만 표시
                print(f"   📄 {file.name}")
            if len(files) > 5:
                print(f"   ... 외 {len(files)-5}개 파일 더")
            
            total_files += len(files)
        else:
            print(f"⚠️  {folder} 폴더가 없습니다.")
    
    print(f"\n📊 총 {total_files}개의 문서 파일이 발견되었습니다.")
    
    # 실제 RAG 시스템 로딩 (패키지 설치 후 활성화)
    try:
        # from power_market_rag import PowerMarketRAG
        # rag = PowerMarketRAG()
        # 
        # if rag.initialize():
        #     print("✅ RAG 시스템 초기화 완료")
        #     
        #     for folder in document_folders:
        #         if Path(folder).exists():
        #             print(f"📚 {folder} 폴더 로딩 중...")
        #             success = rag.load_documents(folder)
        #             if success:
        #                 print(f"✅ {folder} 폴더 로딩 완료")
        #             else:
        #                 print(f"❌ {folder} 폴더 로딩 실패")
        #     
        #     # 시스템 상태 확인
        #     stats = rag.get_system_status()
        #     print(f"📈 최종 시스템 상태: {stats}")
        # else:
        #     print("❌ RAG 시스템 초기화 실패")
        
        print("\n💡 RAG 시스템을 실제로 사용하려면:")
        print("1. 먼저 패키지를 설치하세요: ./install.sh")
        print("2. 시스템을 실행하세요: ./run.sh")
        print("3. 웹 인터페이스에서 질문해보세요!")
        
    except ImportError:
        print("\n📦 아직 패키지가 설치되지 않았습니다.")
        print("다음 명령어로 설치 후 다시 실행하세요:")
        print("  chmod +x install.sh && ./install.sh")

def show_sample_questions():
    """예시 질문들 보여주기"""
    print("\n❓ 이제 이런 질문들을 할 수 있습니다:")
    
    sample_questions = [
        "전력시장운영규칙 제16.4.1조의 내용은 무엇인가요?",
        "하루전발전계획 수립 절차를 자세히 설명해주세요",
        "실시간 급전운영 절차는 어떻게 되나요?",
        "계통운영 기준에서 주파수 관리는 어떻게 하나요?",
        "정산 기준에서 SMP 계산 방법을 알려주세요",
        "입찰운영 절차에서 가격 입찰 방식은?",
        "제주 시범사업의 발전계획 수립은 어떻게 다른가요?",
        "비상시 급전지시 절차는 무엇인가요?",
        "수요반응자원의 정산 규칙을 설명해주세요",
        "연료제약발전기의 운영 방식은?"
    ]
    
    for i, question in enumerate(sample_questions, 1):
        print(f"{i:2}. {question}")

if __name__ == "__main__":
    print("🔍 전력시장운영규칙 문서 현황을 확인합니다...\n")
    load_power_market_documents()
    show_sample_questions()
    
    print("\n" + "="*60)
    print("🎯 다음 단계:")
    print("1. ./install.sh 실행으로 패키지 설치")
    print("2. ./run.sh 실행으로 시스템 시작") 
    print("3. http://localhost:8000 에서 전력시장 전문가 AI 활용!")
    print("="*60)
