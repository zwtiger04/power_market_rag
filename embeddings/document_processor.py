"""
문서 처리 모듈
- PDF, 텍스트, Word 파일을 읽어서 텍스트로 변환
- 텍스트를 적절한 크기로 나누기 (chunking)
"""

import os
import logging
from typing import List, Dict
from pathlib import Path

import PyPDF2
from docx import Document
import pandas as pd

class DocumentProcessor:
    """문서를 처리하고 텍스트를 추출하는 클래스"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Args:
            chunk_size: 텍스트를 나누는 크기 (글자 수)
            chunk_overlap: 겹치는 부분의 크기 (글자 수)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.logger = logging.getLogger(__name__)
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """PDF 파일에서 텍스트를 추출합니다"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                # 각 페이지에서 텍스트 추출
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
                
                return text.strip()
        except Exception as e:
            self.logger.error(f"PDF 읽기 오류 {file_path}: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Word 파일에서 텍스트를 추출합니다"""
        try:
            doc = Document(file_path)
            text = ""
            
            # 각 문단에서 텍스트 추출
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
        except Exception as e:
            self.logger.error(f"Word 파일 읽기 오류 {file_path}: {e}")
            return ""
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """텍스트 파일에서 내용을 읽습니다"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            self.logger.error(f"텍스트 파일 읽기 오류 {file_path}: {e}")
            return ""
    
    def process_file(self, file_path: str) -> str:
        """파일 확장자에 따라 적절한 방법으로 텍스트를 추출합니다"""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return self.extract_text_from_pdf(str(file_path))
        elif extension == '.docx':
            return self.extract_text_from_docx(str(file_path))
        elif extension in ['.txt', '.md']:
            return self.extract_text_from_txt(str(file_path))
        else:
            self.logger.warning(f"지원하지 않는 파일 형식: {extension}")
            return ""
    
    def split_text_into_chunks(self, text: str) -> List[Dict[str, any]]:
        """긴 텍스트를 작은 조각들로 나눕니다"""
        chunks = []
        
        # 텍스트를 문장 단위로 나누기
        sentences = text.split('. ')
        
        current_chunk = ""
        chunk_id = 0
        
        for sentence in sentences:
            # 현재 조각에 문장을 추가했을 때 크기 확인
            potential_chunk = current_chunk + sentence + ". "
            
            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # 현재 조각이 비어있지 않으면 저장
                if current_chunk.strip():
                    chunks.append({
                        'id': chunk_id,
                        'text': current_chunk.strip(),
                        'length': len(current_chunk)
                    })
                    chunk_id += 1
                
                # 새로운 조각 시작
                # 겹치는 부분 계산
                if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + sentence + ". "
                else:
                    current_chunk = sentence + ". "
        
        # 마지막 조각 저장
        if current_chunk.strip():
            chunks.append({
                'id': chunk_id,
                'text': current_chunk.strip(),
                'length': len(current_chunk)
            })
        
        return chunks
    
    def process_documents_from_directory(self, directory_path: str) -> List[Dict[str, any]]:
        """디렉토리에 있는 모든 문서를 처리합니다"""
        all_chunks = []
        directory = Path(directory_path)
        
        if not directory.exists():
            self.logger.error(f"디렉토리가 존재하지 않습니다: {directory_path}")
            return all_chunks
        
        supported_extensions = ['.pdf', '.docx', '.txt', '.md']
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                self.logger.info(f"처리 중인 파일: {file_path}")
                
                # 파일에서 텍스트 추출
                text = self.process_file(str(file_path))
                
                if text:
                    # 텍스트를 조각으로 나누기
                    chunks = self.split_text_into_chunks(text)
                    
                    # 메타데이터 추가
                    for chunk in chunks:
                        chunk.update({
                            'source_file': str(file_path),
                            'file_name': file_path.name,
                            'file_type': file_path.suffix.lower()
                        })
                    
                    all_chunks.extend(chunks)
                    self.logger.info(f"파일 {file_path.name}에서 {len(chunks)}개 조각 생성")
        
        self.logger.info(f"총 {len(all_chunks)}개의 텍스트 조각이 처리되었습니다")
        return all_chunks

if __name__ == "__main__":
    # 테스트 코드
    processor = DocumentProcessor()
    
    # 예시 텍스트로 테스트
    sample_text = """
    전력시장운영규칙에 따르면 발전계획 수립은 매우 중요한 절차입니다. 
    하루전발전계획은 전력거래일 전일에 수립되며, 당일발전계획은 매시간마다 
    갱신됩니다. 실시간발전계획은 15분 단위로 운영되어 계통의 안정성을 
    보장합니다. 이러한 다단계 발전계획 시스템은 전력 공급의 신뢰성과 
    경제성을 동시에 확보하는 핵심 메커니즘입니다.
    """
    
    chunks = processor.split_text_into_chunks(sample_text)
    print(f"생성된 조각 수: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"조각 {i+1}: {chunk['text'][:100]}...")
