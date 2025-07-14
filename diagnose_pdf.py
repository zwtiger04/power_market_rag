#!/usr/bin/env python3
"""
PDF 처리 진단 스크립트
PyMuPDF가 PDF를 제대로 읽을 수 있는지 확인
"""

import fitz  # PyMuPDF
from pathlib import Path
import sys

def diagnose_pdf(pdf_path):
    """PDF 파일 진단"""
    print(f"\n=== PDF 진단: {pdf_path.name} ===")
    
    try:
        # 파일 존재 확인
        if not pdf_path.exists():
            print(f"❌ 파일이 존재하지 않습니다: {pdf_path}")
            return False
        
        # 파일 크기 확인
        file_size = pdf_path.stat().st_size
        print(f"📄 파일 크기: {file_size:,} bytes")
        
        # PyMuPDF로 PDF 열기
        doc = fitz.open(pdf_path)
        print(f"📊 총 페이지 수: {len(doc)}")
        
        if len(doc) == 0:
            print("❌ PDF에 페이지가 없습니다")
            doc.close()
            return False
        
        # 첫 번째 페이지 텍스트 추출 테스트
        page = doc.load_page(0)
        text = page.get_text()
        
        print(f"📝 첫 페이지 텍스트 길이: {len(text)} 문자")
        
        if text.strip():
            print("✅ 텍스트 추출 성공")
            print(f"📄 첫 100자: {text[:100]}...")
        else:
            print("⚠️  첫 페이지에서 텍스트를 추출할 수 없습니다")
            
            # 이미지 또는 스캔된 PDF인지 확인
            images = page.get_images()
            print(f"🖼️  첫 페이지 이미지 수: {len(images)}")
            
            if len(images) > 0:
                print("💡 스캔된 PDF이거나 이미지 기반 PDF일 수 있습니다")
        
        # 페이지별 텍스트 길이 확인
        page_texts = []
        for i in range(min(3, len(doc))):  # 최대 3페이지만 확인
            page = doc.load_page(i)
            page_text = page.get_text()
            page_texts.append(len(page_text))
            print(f"📄 페이지 {i+1} 텍스트 길이: {len(page_text)} 문자")
        
        doc.close()
        
        total_text_length = sum(page_texts)
        print(f"📊 전체 텍스트 길이 (처음 3페이지): {total_text_length} 문자")
        
        return total_text_length > 0
        
    except Exception as e:
        print(f"❌ PDF 처리 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("PDF 처리 진단 도구")
    print("=" * 50)
    
    docs_dir = Path("data/documents")
    
    if not docs_dir.exists():
        print(f"❌ 문서 디렉토리가 존재하지 않습니다: {docs_dir}")
        return
    
    # PDF 파일 찾기
    pdf_files = list(docs_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ PDF 파일을 찾을 수 없습니다: {docs_dir}")
        return
    
    print(f"📁 발견된 PDF 파일 수: {len(pdf_files)}")
    
    # 크기순으로 정렬 (작은 것부터)
    pdf_files_with_size = [(f, f.stat().st_size) for f in pdf_files]
    pdf_files_with_size.sort(key=lambda x: x[1])
    
    # 처음 5개 파일만 테스트
    success_count = 0
    for i, (pdf_file, size) in enumerate(pdf_files_with_size[:5]):
        success = diagnose_pdf(pdf_file)
        if success:
            success_count += 1
    
    print(f"\n📊 결과 요약:")
    print(f"테스트한 파일 수: {min(5, len(pdf_files))}")
    print(f"성공적으로 처리된 파일 수: {success_count}")
    print(f"성공률: {success_count / min(5, len(pdf_files)) * 100:.1f}%")
    
    if success_count == 0:
        print("\n💡 해결 방안:")
        print("1. PDF 파일이 암호로 보호되어 있는지 확인")
        print("2. PDF 파일이 손상되었는지 확인")
        print("3. 스캔된 이미지 기반 PDF인 경우 OCR이 필요할 수 있음")
        print("4. PDF 버전이 너무 새롭거나 특수한 형식일 수 있음")

if __name__ == "__main__":
    main()