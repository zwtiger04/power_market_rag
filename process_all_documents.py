#!/usr/bin/env python3
"""
전체 문서 컬렉션 처리 스크립트
전력시장운영규칙 PDF 문서들을 모두 처리하여 AI 최적화 벡터 데이터베이스 구축
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.multimodal_processor import MultimodalProcessor
from core.metadata_extractor import MetadataExtractor  
from core.vector_engine import VectorEngine

def find_all_pdfs(documents_dir: str) -> List[str]:
    """모든 PDF 파일 찾기"""
    pdf_files = []
    for file_name in os.listdir(documents_dir):
        if file_name.endswith('.pdf') and not file_name.endswith('.pdf:Zone.Identifier'):
            pdf_files.append(os.path.join(documents_dir, file_name))
    return sorted(pdf_files)

def find_processed_documents(processed_dir: str) -> set:
    """이미 처리된 문서 ID 찾기"""
    processed_ids = set()
    if os.path.exists(processed_dir):
        for file_name in os.listdir(processed_dir):
            if file_name.endswith('_processed.json'):
                doc_id = file_name.replace('_processed.json', '')
                processed_ids.add(doc_id)
    return processed_ids

def process_document_batch(pdf_files: List[str], 
                          multimodal_processor: MultimodalProcessor,
                          metadata_extractor: MetadataExtractor,
                          vector_engine: VectorEngine) -> Dict[str, Any]:
    """문서 배치 처리"""
    
    batch_results = {
        'start_time': time.time(),
        'documents_processed': [],
        'success_count': 0,
        'error_count': 0,
        'errors': []
    }
    
    for i, pdf_path in enumerate(pdf_files):
        print(f"\n[{i+1}/{len(pdf_files)}] Processing: {os.path.basename(pdf_path)}")
        
        doc_result = {
            'document_path': pdf_path,
            'document_name': os.path.basename(pdf_path),
            'start_time': time.time(),
            'success': False,
            'error': None
        }
        
        try:
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
            
            doc_result['success'] = True
            doc_result['processing_time'] = time.time() - doc_result['start_time']
            batch_results['success_count'] += 1
            
            print(f"  ✓ Success ({doc_result['processing_time']:.2f}s)")
            
        except Exception as e:
            error_msg = f"Error processing {os.path.basename(pdf_path)}: {str(e)}"
            print(f"  ✗ {error_msg}")
            
            doc_result['error'] = error_msg
            doc_result['processing_time'] = time.time() - doc_result['start_time']
            batch_results['error_count'] += 1
            batch_results['errors'].append(error_msg)
        
        batch_results['documents_processed'].append(doc_result)
    
    batch_results['end_time'] = time.time()
    batch_results['total_duration'] = batch_results['end_time'] - batch_results['start_time']
    
    return batch_results

def save_batch_results(results: Dict[str, Any], output_dir: str):
    """배치 처리 결과 저장"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = int(time.time())
    results_file = os.path.join(output_dir, f'batch_processing_results_{timestamp}.json')
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\nBatch results saved to: {results_file}")
    return results_file

def print_summary(results: Dict[str, Any]):
    """처리 결과 요약 출력"""
    total_docs = len(results['documents_processed'])
    success_rate = (results['success_count'] / total_docs * 100) if total_docs > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Total documents:     {total_docs}")
    print(f"Successfully processed: {results['success_count']}")
    print(f"Failed:             {results['error_count']}")
    print(f"Success rate:       {success_rate:.1f}%")
    print(f"Total time:         {results['total_duration']:.2f}s")
    
    if results['errors']:
        print(f"\nErrors encountered:")
        for error in results['errors']:
            print(f"  - {error}")

def main():
    """메인 실행 함수"""
    print("AI 최적화 벡터 데이터베이스 구축을 시작합니다...")
    
    # 경로 설정
    documents_dir = "data/documents"
    processed_dir = "data/processed"
    results_dir = "data/batch_results"
    
    # 모든 PDF 파일 찾기
    pdf_files = find_all_pdfs(documents_dir)
    print(f"Found {len(pdf_files)} PDF documents")
    
    # 이미 처리된 문서 확인
    processed_ids = find_processed_documents(processed_dir)
    print(f"Already processed: {len(processed_ids)} documents")
    
    # 미처리 문서 필터링
    remaining_files = []
    for pdf_path in pdf_files:
        doc_name = os.path.basename(pdf_path)
        doc_id = doc_name.replace('.pdf', '')
        if doc_id not in processed_ids:
            remaining_files.append(pdf_path)
    
    print(f"Remaining to process: {len(remaining_files)} documents")
    
    if not remaining_files:
        print("All documents already processed!")
        return
    
    try:
        # 컴포넌트 초기화
        print("\nInitializing components...")
        multimodal_processor = MultimodalProcessor()
        metadata_extractor = MetadataExtractor()
        vector_engine = VectorEngine()
        
        # 배치 처리 실행
        print(f"\nStarting batch processing of {len(remaining_files)} documents...")
        results = process_document_batch(
            remaining_files,
            multimodal_processor,
            metadata_extractor,
            vector_engine
        )
        
        # 결과 저장 및 요약
        save_batch_results(results, results_dir)
        print_summary(results)
        
        # 최종 벡터 엔진 상태 확인
        print(f"\nFinal vector database state:")
        try:
            # ChromaDB 컬렉션 상태 확인
            if vector_engine.chroma_client:
                collections = vector_engine.chroma_client.list_collections()
                for collection in collections:
                    count = collection.count()
                    print(f"  {collection.name}: {count} items")
        except Exception as e:
            print(f"  Error checking collections: {e}")
        
    except Exception as e:
        print(f"\nCritical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()