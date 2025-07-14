#!/usr/bin/env python3
"""
PowerMarketRules 문서를 벡터 DB로 변환하는 스크립트
"""

import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from embeddings.document_processor import DocumentProcessor
from embeddings.text_embedder import PowerMarketEmbedder, TextEmbedder
from vector_db.vector_store import VectorDatabase

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_power_market_rules():
    """PowerMarketRules 폴더의 PDF 파일들을 벡터 DB로 변환"""
    
    # 1. 초기화
    logger.info("시스템 초기화 중...")
    
    # 문서 처리기 초기화
    doc_processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
    
    # 임베딩 모델 초기화
    embedder = TextEmbedder()
    
    # 벡터 DB 초기화 (기존 DB에 추가)
    vector_db = VectorDatabase(
        db_path="./vector_db",
        collection_name="power_market_docs"
    )
    
    # 2. PowerMarketRules 폴더 처리
    power_market_folder = Path("PowerMarketRules")
    
    if not power_market_folder.exists():
        logger.error("PowerMarketRules 폴더를 찾을 수 없습니다.")
        return
    
    # PDF 파일 목록 가져오기
    pdf_files = list(power_market_folder.glob("*.pdf"))
    
    # 취업활동증명서 제외
    pdf_files = [f for f in pdf_files if "취업활동증명서" not in f.name]
    
    logger.info(f"총 {len(pdf_files)}개의 PDF 파일을 처리합니다.")
    
    # 3. 각 PDF 파일 처리
    total_chunks = 0
    
    for pdf_file in pdf_files:
        logger.info(f"처리 중: {pdf_file.name}")
        
        try:
            # PDF에서 텍스트 추출
            text = doc_processor.extract_text_from_pdf(str(pdf_file))
            
            if not text:
                logger.warning(f"{pdf_file.name} 파일에서 텍스트를 추출할 수 없습니다.")
                continue
            
            # 텍스트를 청크로 분할
            chunks = doc_processor.split_text_into_chunks(text)
            
            logger.info(f"{pdf_file.name}: {len(chunks)}개의 청크 생성")
            
            # 각 청크에 대해 임베딩 생성 및 메타데이터 준비
            documents = []
            
            for i, chunk_dict in enumerate(chunks):
                # 청크에서 텍스트 추출
                chunk_text = chunk_dict['text'] if isinstance(chunk_dict, dict) else chunk_dict
                
                # 임베딩 생성
                embedding = embedder.encode_text(chunk_text)
                
                # 문서 데이터 구성
                doc_data = {
                    'id': f"{pdf_file.stem}_{i}",
                    'text': chunk_text,
                    'embedding': embedding,
                    'file_name': pdf_file.name,
                    'source_file': str(pdf_file),
                    'file_type': '.pdf',
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
                
                documents.append(doc_data)
            
            # 벡터 DB에 추가
            success = vector_db.add_documents(documents)
            
            if success:
                logger.info(f"✅ {pdf_file.name} 처리 완료")
                total_chunks += len(chunks)
            else:
                logger.error(f"❌ {pdf_file.name} DB 추가 실패")
                
        except Exception as e:
            logger.error(f"{pdf_file.name} 처리 중 오류 발생: {e}")
            continue
    
    # 4. 처리 결과 출력
    logger.info(f"\n{'='*50}")
    logger.info(f"처리 완료!")
    logger.info(f"총 {len(pdf_files)}개 파일에서 {total_chunks}개 청크 생성")
    
    # DB 통계 출력
    stats = vector_db.get_collection_stats()
    logger.info(f"벡터 DB 현재 문서 수: {stats.get('document_count', 0)}")
    logger.info(f"{'='*50}")

if __name__ == "__main__":
    process_power_market_rules()