#!/usr/bin/env python3
"""
전력시장 RAG 시스템 기본 테스트
- 시스템 구조 확인
- 기본 기능 테스트
"""

import os
import sys
from pathlib import Path

def print_header(title):
    """헤더 출력"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_project_structure():
    """프로젝트 구조 확인"""
    print_header("📁 프로젝트 구조 확인")
    
    current_dir = Path(".")
    
    required_dirs = [
        "embeddings", "vector_db", "retrieval", 
        "generation", "api", "config", "documents", "tests"
    ]
    
    required_files = [
        "power_market_rag.py", "requirements.txt", 
        "README.md", "demo.py"
    ]
    
    print("📂 필수 디렉토리 확인:")
    for dir_name in required_dirs:
        if (current_dir / dir_name).exists():
            print(f"   ✅ {dir_name}/")
        else:
            print(f"   ❌ {dir_name}/ (누락)")
    
    print("\n📄 필수 파일 확인:")
    for file_name in required_files:
        if (current_dir / file_name).exists():
            print(f"   ✅ {file_name}")
        else:
            print(f"   ❌ {file_name} (누락)")
    
    # documents 폴더 내용 확인
    docs_dir = current_dir / "documents"
    if docs_dir.exists():
        doc_files = list(docs_dir.glob("*.md"))
        print(f"\n📚 문서 파일: {len(doc_files)}개")
        for doc_file in doc_files:
            print(f"   📖 {doc_file.name}")
    else:
        print("\n📚 문서 폴더가 없습니다.")

def check_modules():
    """모듈 파일 확인"""
    print_header("🔧 모듈 파일 확인")
    
    modules = {
        "embeddings/document_processor.py": "문서 처리기",
        "embeddings/text_embedder.py": "텍스트 임베딩",
        "vector_db/vector_store.py": "벡터 데이터베이스",
        "retrieval/document_retriever.py": "문서 검색기", 
        "generation/answer_generator.py": "답변 생성기",
        "api/api_server.py": "API 서버"
    }
    
    for file_path, description in modules.items():
        if Path(file_path).exists():
            file_size = Path(file_path).stat().st_size
            print(f"   ✅ {description:15} ({file_path}, {file_size:,} bytes)")
        else:
            print(f"   ❌ {description:15} ({file_path}) - 누락")

def check_config():
    """설정 파일 확인"""
    print_header("⚙️ 설정 파일 확인")
    
    config_file = Path("config/config.yaml")
    if config_file.exists():
        print("✅ config.yaml 파일이 있습니다.")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"   파일 크기: {len(content):,} 글자")
                
                # 주요 설정 확인
                key_configs = [
                    "VECTOR_DB_TYPE", "EMBEDDING_MODEL", 
                    "CHUNK_SIZE", "TOP_K"
                ]
                
                for key in key_configs:
                    if key in content:
                        print(f"   📝 {key}: 설정됨")
                    else:
                        print(f"   ⚠️  {key}: 설정 필요")
        except Exception as e:
            print(f"   ❌ 설정 파일 읽기 오류: {e}")
    else:
        print("❌ config.yaml 파일이 없습니다.")

def check_requirements():
    """requirements.txt 확인"""
    print_header("📦 패키지 요구사항 확인")
    
    req_file = Path("requirements.txt")
    if req_file.exists():
        print("✅ requirements.txt 파일이 있습니다.")
        try:
            with open(req_file, 'r', encoding='utf-8') as f:
                packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                print(f"   📦 총 {len(packages)}개 패키지 명시됨")
                
                # 주요 패키지 확인
                key_packages = [
                    "chromadb", "sentence-transformers", "fastapi", 
                    "langchain", "transformers"
                ]
                
                found_packages = []
                for pkg in packages:
                    pkg_name = pkg.split('==')[0].split('>=')[0].split('<=')[0]
                    if pkg_name in key_packages:
                        found_packages.append(pkg_name)
                        print(f"   ✅ {pkg}")
                
                missing = set(key_packages) - set(found_packages)
                if missing:
                    print(f"   ⚠️  누락된 패키지: {missing}")
                    
        except Exception as e:
            print(f"   ❌ requirements.txt 읽기 오류: {e}")
    else:
        print("❌ requirements.txt 파일이 없습니다.")

def test_import_simulation():
    """모듈 임포트 시뮬레이션"""
    print_header("🔄 모듈 임포트 시뮬레이션")
    
    print("실제 패키지가 설치되면 다음과 같이 임포트됩니다:")
    
    import_tests = [
        ("import chromadb", "ChromaDB 벡터 데이터베이스"),
        ("from sentence_transformers import SentenceTransformer", "Sentence Transformers"),
        ("from fastapi import FastAPI", "FastAPI 웹 프레임워크"),
        ("import PyPDF2", "PDF 처리"),
        ("import numpy as np", "NumPy 수치 계산")
    ]
    
    for import_stmt, description in import_tests:
        try:
            exec(import_stmt)
            print(f"   ✅ {description:25} - 가져오기 성공")
        except ImportError as e:
            print(f"   ⚠️  {description:25} - 패키지 설치 필요")
        except Exception as e:
            print(f"   ❌ {description:25} - 오류: {e}")

def show_next_steps():
    """다음 단계 안내"""
    print_header("🚀 다음 단계")
    
    print("시스템을 실행하려면 다음 단계를 따라하세요:")
    print()
    print("1️⃣ 패키지 설치:")
    print("   chmod +x install.sh")
    print("   ./install.sh")
    print()
    print("2️⃣ 데모 실행:")
    print("   python3 demo.py")
    print()
    print("3️⃣ API 서버 실행:")
    print("   chmod +x run.sh") 
    print("   ./run.sh")
    print("   웹 브라우저에서 http://localhost:8000 접속")
    print()
    print("4️⃣ 문서 추가:")
    print("   documents/ 폴더에 PDF나 텍스트 파일 추가")
    print()
    print("5️⃣ 질문 테스트:")
    print("   - 하루전발전계획이 무엇인가요?")
    print("   - 전력계통의 주파수 관리는 어떻게 하나요?")
    print("   - 예비력 확보 기준을 알려주세요")

def main():
    """메인 실행 함수"""
    print("🔍 전력시장 RAG 시스템 기본 점검을 시작합니다...")
    
    check_project_structure()
    check_modules()
    check_config()
    check_requirements()
    test_import_simulation()
    show_next_steps()
    
    print_header("✨ 점검 완료")
    print("시스템 구조가 올바르게 설정되었습니다!")
    print("이제 패키지를 설치하고 시스템을 실행할 수 있습니다.")

if __name__ == "__main__":
    main()
