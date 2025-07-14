#!/usr/bin/env python3
"""
단일 문서 처리 스크립트
"""

import sys
import json
import time
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.multimodal_processor import MultimodalProcessor
from core.metadata_extractor import MetadataExtractor  
from core.vector_engine import VectorEngine

def process_single_document(pdf_path: str):
    """단일 문서 처리"""
    
    print(f"Processing: {pdf_path}")
    
    try:
        # 컴포넌트 초기화
        multimodal_processor = MultimodalProcessor()
        metadata_extractor = MetadataExtractor()
        vector_engine = VectorEngine()
        
        start_time = time.time()
        
        # 1. 멀티모달 처리
        print("  → Multimodal processing...")
        processed_doc = multimodal_processor.process_document(pdf_path)
        
        if not processed_doc:
            raise ValueError("멀티모달 처리 실패")
        
        # 2. 메타데이터 추출
        print("  → Metadata extraction...")
        metadata = metadata_extractor.extract_metadata(processed_doc)
        
        # 3. 벡터 통합
        print("  → Vector integration...")
        doc_id = processed_doc['document_id']
        vector_result = vector_engine.add_document(
            doc_id,
            processed_doc['content'],
            metadata
        )
        
        processing_time = time.time() - start_time
        
        print(f"  ✓ Success ({processing_time:.2f}s)")
        
        # 컬렉션 상태 확인
        try:
            if vector_engine.chroma_client:
                collections = vector_engine.chroma_client.list_collections()
                print(f"  Collections:")
                for collection in collections:
                    count = collection.count()
                    print(f"    {collection.name}: {count} items")
        except Exception as e:
            print(f"  Error checking collections: {e}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python process_single_doc.py <pdf_file_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    success = process_single_document(pdf_path)
    
    if success:
        print("Document processed successfully!")
    else:
        print("Document processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()