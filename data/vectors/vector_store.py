"""
벡터 데이터베이스 모듈
- 임베딩된 벡터들을 저장하고 검색
- ChromaDB를 사용한 벡터 저장소 구현
"""

import logging
import os
from typing import List, Dict, Optional, Union
import numpy as np
import chromadb
from chromadb.config import Settings
import uuid
import json

class VectorDatabase:
    """벡터 데이터베이스 클래스"""
    
    def __init__(self, 
                 db_path: str = "./vector_db",
                 collection_name: str = "power_market_docs"):
        """
        Args:
            db_path: 데이터베이스 저장 경로
            collection_name: 컬렉션(테이블) 이름
        """
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.collection_name = collection_name
        
        # 데이터베이스 디렉토리 생성
        os.makedirs(db_path, exist_ok=True)
        
        try:
            # ChromaDB 클라이언트 초기화
            self.client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(
                    anonymized_telemetry=False  # 텔레메트리 비활성화
                )
            )
            
            # 컬렉션 생성 또는 가져오기
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "전력시장 문서 벡터 저장소"}
            )
            
            self.logger.info(f"벡터 데이터베이스 초기화 완료: {db_path}")
            
        except Exception as e:
            self.logger.error(f"벡터 데이터베이스 초기화 실패: {e}")
            raise
    
    def add_documents(self, documents: List[Dict[str, any]]) -> bool:
        """문서들을 벡터 데이터베이스에 추가"""
        try:
            if not documents:
                self.logger.warning("추가할 문서가 없습니다")
                return False
            
            # 데이터 준비
            ids = []
            embeddings = []
            metadatas = []
            documents_text = []
            
            for doc in documents:
                # 고유 ID 생성 (파일명 + 조각 ID)
                doc_id = f"{doc.get('file_name', 'unknown')}_{doc.get('id', uuid.uuid4())}"
                ids.append(doc_id)
                
                # 임베딩 벡터
                embedding = doc.get('embedding', [])
                if isinstance(embedding, np.ndarray):
                    embedding = embedding.tolist()
                embeddings.append(embedding)
                
                # 메타데이터 (임베딩 제외한 모든 정보)
                metadata = {k: v for k, v in doc.items() 
                           if k not in ['embedding', 'text'] and v is not None}
                
                # 메타데이터 값들을 문자열로 변환 (ChromaDB 요구사항)
                for key, value in metadata.items():
                    if not isinstance(value, (str, int, float, bool)):
                        metadata[key] = str(value)
                
                metadatas.append(metadata)
                
                # 문서 텍스트
                documents_text.append(doc.get('text', ''))
            
            # 데이터베이스에 추가
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            
            self.logger.info(f"{len(documents)}개 문서를 벡터 데이터베이스에 추가했습니다")
            return True
            
        except Exception as e:
            self.logger.error(f"문서 추가 실패: {e}")
            return False
    
    def search_similar(self, 
                      query_embedding: Union[np.ndarray, List[float]], 
                      top_k: int = 5,
                      where: Optional[Dict] = None) -> List[Dict[str, any]]:
        """유사한 문서 검색"""
        try:
            # numpy 배열을 리스트로 변환
            if isinstance(query_embedding, np.ndarray):
                query_embedding = query_embedding.tolist()
            
            # 검색 실행
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where  # 메타데이터 필터링
            )
            
            # 결과 포맷팅
            formatted_results = []
            
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i] if results['documents'] else '',
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0,
                        'similarity': 1 - results['distances'][0][i] if results['distances'] else 1.0
                    }
                    formatted_results.append(result)
            
            self.logger.info(f"{len(formatted_results)}개의 유사 문서를 찾았습니다")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"유사 문서 검색 실패: {e}")
            return []
    
    def search_by_text(self, 
                      query_text: str, 
                      top_k: int = 5,
                      where: Optional[Dict] = None) -> List[Dict[str, any]]:
        """텍스트로 직접 검색 (ChromaDB의 텍스트 검색 기능 사용)"""
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=where
            )
            
            # 결과 포맷팅
            formatted_results = []
            
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i] if results['documents'] else '',
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0,
                        'similarity': 1 - results['distances'][0][i] if results['distances'] else 1.0
                    }
                    formatted_results.append(result)
            
            self.logger.info(f"텍스트 '{query_text}'로 {len(formatted_results)}개 문서를 찾았습니다")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"텍스트 검색 실패: {e}")
            return []
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, any]]:
        """ID로 특정 문서 가져오기"""
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=['metadatas', 'documents', 'embeddings']
            )
            
            if results['ids'] and len(results['ids']) > 0:
                return {
                    'id': results['ids'][0],
                    'text': results['documents'][0] if results['documents'] else '',
                    'metadata': results['metadatas'][0] if results['metadatas'] else {},
                    'embedding': results['embeddings'][0] if results['embeddings'] else []
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"문서 조회 실패 (ID: {doc_id}): {e}")
            return None
    
    def delete_documents(self, doc_ids: List[str]) -> bool:
        """문서들 삭제"""
        try:
            self.collection.delete(ids=doc_ids)
            self.logger.info(f"{len(doc_ids)}개 문서를 삭제했습니다")
            return True
            
        except Exception as e:
            self.logger.error(f"문서 삭제 실패: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """컬렉션의 모든 데이터 삭제"""
        try:
            # 컬렉션 삭제 후 재생성
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "전력시장 문서 벡터 저장소"}
            )
            
            self.logger.info("컬렉션을 초기화했습니다")
            return True
            
        except Exception as e:
            self.logger.error(f"컬렉션 초기화 실패: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, any]:
        """컬렉션 통계 정보"""
        try:
            count = self.collection.count()
            
            return {
                'document_count': count,
                'collection_name': self.collection_name,
                'db_path': self.db_path
            }
            
        except Exception as e:
            self.logger.error(f"통계 조회 실패: {e}")
            return {}
    
    def filter_by_source(self, source_file: str, top_k: int = 10) -> List[Dict[str, any]]:
        """특정 소스 파일에서 온 문서들만 조회"""
        try:
            results = self.collection.get(
                where={"source_file": {"$eq": source_file}},
                limit=top_k,
                include=['metadatas', 'documents']
            )
            
            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    result = {
                        'id': results['ids'][i],
                        'text': results['documents'][i] if results['documents'] else '',
                        'metadata': results['metadatas'][i] if results['metadatas'] else {}
                    }
                    formatted_results.append(result)
            
            self.logger.info(f"소스 파일 '{source_file}'에서 {len(formatted_results)}개 문서를 찾았습니다")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"소스 파일 필터링 실패: {e}")
            return []

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    # 테스트용 데이터베이스 생성
    vector_db = VectorDatabase(
        db_path="./test_vector_db",
        collection_name="test_collection"
    )
    
    # 테스트용 문서 데이터
    test_documents = [
        {
            'id': 0,
            'text': '전력시장에서 발전계획 수립은 매우 중요합니다.',
            'embedding': np.random.rand(384).tolist(),  # 테스트용 랜덤 벡터
            'file_name': 'test1.txt',
            'source_file': '/test/test1.txt',
            'file_type': '.txt'
        },
        {
            'id': 1,
            'text': '계통운영자는 실시간으로 전력 수급을 관리합니다.',
            'embedding': np.random.rand(384).tolist(),
            'file_name': 'test2.txt',
            'source_file': '/test/test2.txt',
            'file_type': '.txt'
        }
    ]
    
    # 문서 추가 테스트
    success = vector_db.add_documents(test_documents)
    print(f"문서 추가 성공: {success}")
    
    # 통계 정보 조회
    stats = vector_db.get_collection_stats()
    print(f"컬렉션 통계: {stats}")
    
    # 텍스트 검색 테스트
    search_results = vector_db.search_by_text("발전계획", top_k=2)
    print(f"검색 결과 수: {len(search_results)}")
    for result in search_results:
        print(f"- ID: {result['id']}, 유사도: {result['similarity']:.4f}")
        print(f"  텍스트: {result['text'][:50]}...")
    
    # 정리
    vector_db.clear_collection()
    print("테스트 완료 및 정리")
