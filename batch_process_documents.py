#!/usr/bin/env python3
"""
전체 문서 자동 처리 스크립트
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.multimodal_processor import MultimodalProcessor
from core.metadata_extractor import MetadataExtractor  
from core.vector_engine import VectorEngine

def find_remaining_documents():
    """처리되지 않은 문서들을 찾기"""
    documents_dir = "data/documents"
    processed_dir = "data/processed"
    
    # 모든 PDF 파일 찾기
    all_pdfs = []
    for file_name in os.listdir(documents_dir):
        if file_name.endswith('.pdf') and not file_name.endswith('.pdf:Zone.Identifier'):
            all_pdfs.append(os.path.join(documents_dir, file_name))
    
    # 이미 처리된 문서 ID 찾기
    processed_ids = set()
    if os.path.exists(processed_dir):
        for file_name in os.listdir(processed_dir):
            if file_name.endswith('_processed.json'):
                doc_id = file_name.replace('_processed.json', '')
                processed_ids.add(doc_id)
    
    # 미처리 문서 필터링
    remaining_files = []
    for pdf_path in all_pdfs:
        doc_name = os.path.basename(pdf_path)
        doc_id = doc_name.replace('.pdf', '')
        if doc_id not in processed_ids:
            remaining_files.append(pdf_path)
    
    return sorted(remaining_files)

def process_documents_batch(pdf_files: List[str], start_idx: int = 0, batch_size: int = 5):
    """문서들을 배치로 처리"""
    
    # 컴포넌트 초기화
    multimodal_processor = MultimodalProcessor()
    metadata_extractor = MetadataExtractor()
    vector_engine = VectorEngine()
    
    results = {
        'start_time': time.time(),
        'processed': [],
        'failed': [],
        'total_processed': 0
    }
    
    # 처리할 파일 범위 결정
    end_idx = min(start_idx + batch_size, len(pdf_files))
    batch_files = pdf_files[start_idx:end_idx]
    
    print(f"Processing documents {start_idx+1}-{end_idx} of {len(pdf_files)}")
    
    for i, pdf_path in enumerate(batch_files):
        current_idx = start_idx + i + 1
        print(f"\n[{current_idx}/{len(pdf_files)}] Processing: {os.path.basename(pdf_path)}")
        
        doc_start_time = time.time()
        
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
            
            processing_time = time.time() - doc_start_time
            
            print(f"  ✓ Success ({processing_time:.2f}s)")
            
            results['processed'].append({
                'file': os.path.basename(pdf_path),
                'doc_id': doc_id,
                'processing_time': processing_time
            })
            results['total_processed'] += 1
            
        except Exception as e:
            processing_time = time.time() - doc_start_time
            error_msg = str(e)
            
            print(f"  ✗ Error: {error_msg} ({processing_time:.2f}s)")
            
            results['failed'].append({
                'file': os.path.basename(pdf_path),
                'error': error_msg,
                'processing_time': processing_time
            })
    
    results['end_time'] = time.time()
    results['total_duration'] = results['end_time'] - results['start_time']
    
    # 컬렉션 상태 확인
    try:
        if vector_engine.chroma_client:
            collections = vector_engine.chroma_client.list_collections()
            results['collections_status'] = {}
            for collection in collections:
                count = collection.count()
                results['collections_status'][collection.name] = count
    except Exception as e:
        results['collections_status'] = f"Error: {e}"
    
    return results

def save_progress(results: dict, batch_num: int):
    """진행 상황 저장"""
    os.makedirs("data/batch_progress", exist_ok=True)
    timestamp = int(time.time())
    
    filename = f"data/batch_progress/batch_{batch_num}_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\nProgress saved to: {filename}")

def print_batch_summary(results: dict, batch_num: int):
    """배치 처리 결과 요약"""
    success_count = len(results['processed'])
    failed_count = len(results['failed'])
    total_count = success_count + failed_count
    
    print(f"\n{'='*60}")
    print(f"BATCH {batch_num} SUMMARY")
    print(f"{'='*60}")
    print(f"Total processed:    {total_count}")
    print(f"Successful:         {success_count}")
    print(f"Failed:             {failed_count}")
    print(f"Success rate:       {(success_count/total_count*100):.1f}%" if total_count > 0 else "Success rate: 0%")
    print(f"Total time:         {results['total_duration']:.2f}s")
    
    if 'collections_status' in results and isinstance(results['collections_status'], dict):
        print(f"\nVector Database Status:")
        for collection_name, count in results['collections_status'].items():
            print(f"  {collection_name}: {count} items")
    
    if results['failed']:
        print(f"\nFailed documents:")
        for failed in results['failed']:
            print(f"  - {failed['file']}: {failed['error']}")

def main():
    print("AI 최적화 벡터 데이터베이스 자동 구축을 시작합니다...")
    
    # 처리되지 않은 문서들 찾기
    remaining_files = find_remaining_documents()
    
    if not remaining_files:
        print("모든 문서가 이미 처리되었습니다!")
        return
    
    print(f"처리할 문서: {len(remaining_files)}개")
    
    # 배치 크기 설정 (메모리를 고려하여 작게)
    batch_size = 3
    total_batches = (len(remaining_files) + batch_size - 1) // batch_size
    
    # 배치별로 처리
    for batch_num in range(1, total_batches + 1):
        start_idx = (batch_num - 1) * batch_size
        
        print(f"\n{'='*60}")
        print(f"BATCH {batch_num}/{total_batches}")
        print(f"{'='*60}")
        
        try:
            results = process_documents_batch(remaining_files, start_idx, batch_size)
            
            # 결과 저장 및 출력
            save_progress(results, batch_num)
            print_batch_summary(results, batch_num)
            
            # 실패가 많으면 잠시 대기
            if len(results['failed']) >= 2:
                print(f"\n실패한 문서가 많습니다. 5초 대기...")
                time.sleep(5)
            
        except Exception as e:
            print(f"\nBatch {batch_num} 처리 중 오류 발생: {e}")
            continue
    
    print(f"\n{'='*60}")
    print("전체 문서 처리 완료!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()