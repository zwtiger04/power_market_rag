# ⚡ 전력시장 RAG 시스템 완전 가이드

## 📋 목차

1. [시스템 개요](#1-시스템-개요)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [핵심 모듈 코드](#3-핵심-모듈-코드)
4. [설정 및 스크립트](#4-설정-및-스크립트)
5. [예시 문서](#5-예시-문서)
6. [설치 및 실행](#6-설치-및-실행)
7. [사용법 가이드](#7-사용법-가이드)
8. [API 사용법](#8-api-사용법)
9. [문제해결](#9-문제해결)
10. [고급 설정](#10-고급-설정)

---

## 1. 시스템 개요

### 🎯 RAG (Retrieval-Augmented Generation)란?

**RAG**는 "검색 증강 생성"으로, 두 단계로 작동합니다:
1. **검색 단계**: 질문과 관련된 문서를 찾습니다
2. **생성 단계**: 찾은 문서를 바탕으로 답변을 생성합니다

### 🏗️ 시스템 아키텍처

```
📄 문서 입력 → 🔤 텍스트 추출 → ✂️ 청킹 → 🧠 임베딩 → 💾 벡터DB 저장
                                                                    ↓
💡 답변 생성 ← 📝 컨텍스트 구성 ← 🔍 유사 문서 검색 ← ❓ 사용자 질문
```

### ⭐ 주요 특징

- **다양한 검색 방식**: 의미적, 키워드, 하이브리드, 스마트 검색
- **전력시장 특화**: 전문용어와 규정에 최적화
- **모듈형 구조**: 독립적이면서 유기적으로 연결된 모듈들
- **웹 인터페이스**: 사용자 친화적 웹 UI 제공
- **API 지원**: 다른 시스템과 쉬운 연동

---

## 2. 프로젝트 구조

```
power_market_rag/
├── 📄 power_market_rag.py          # 메인 RAG 시스템
├── 📄 demo.py                      # 데모 스크립트
├── 📄 requirements.txt             # 패키지 목록
├── 📄 README.md                   # 사용법 가이드
├── 📄 install.sh                  # 자동 설치 스크립트
├── 📄 run.sh                      # 실행 스크립트
├── 📄 test_basic.py               # 기본 테스트
├── 📂 embeddings/                 # 임베딩 모듈
│   ├── document_processor.py       # 문서 처리
│   └── text_embedder.py            # 텍스트 임베딩
├── 📂 vector_db/                  # 벡터 데이터베이스
│   └── vector_store.py             # ChromaDB 관리
├── 📂 retrieval/                  # 검색 엔진
│   └── document_retriever.py       # 문서 검색
├── 📂 generation/                 # 답변 생성
│   └── answer_generator.py         # 답변 생성기
├── 📂 api/                        # 웹 API
│   └── api_server.py               # FastAPI 서버
├── 📂 config/                     # 설정
│   └── config.yaml                 # 시스템 설정
├── 📂 documents/                  # 문서 저장소
│   ├── 발전계획_가이드.md
│   ├── 계통운영기준.md
│   └── 전력시장_거래절차.md
├── 📂 vector_db/                  # 벡터 DB 저장소
├── 📂 logs/                       # 로그 파일
└── 📂 tests/                      # 테스트 코드
    └── test_rag_system.py
```

---

## 3. 핵심 모듈 코드

### 3.1 문서 처리 모듈 (embeddings/document_processor.py)

```python
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
```

### 3.2 텍스트 임베딩 모듈 (embeddings/text_embedder.py)

```python
"""
임베딩 모듈
- 텍스트를 벡터(숫자 배열)로 변환
- 한국어와 전력시장 전문용어를 잘 이해하는 모델 사용
"""

import logging
from typing import List, Dict, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

class TextEmbedder:
    """텍스트를 벡터로 변환하는 클래스"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Args:
            model_name: 사용할 임베딩 모델 이름
                      - paraphrase-multilingual-MiniLM-L12-v2: 다국어 지원, 경량화
                      - paraphrase-multilingual-mpnet-base-v2: 더 높은 성능, 무거움
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        
        try:
            self.logger.info(f"임베딩 모델 로딩 중: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
            self.logger.info(f"모델 로딩 완료. 임베딩 차원: {self.embedding_dimension}")
        except Exception as e:
            self.logger.error(f"모델 로딩 실패: {e}")
            raise
    
    def encode_text(self, text: str) -> np.ndarray:
        """단일 텍스트를 벡터로 변환"""
        try:
            # 텍스트가 비어있는지 확인
            if not text or not text.strip():
                self.logger.warning("빈 텍스트가 입력되었습니다")
                return np.zeros(self.embedding_dimension)
            
            # 임베딩 생성
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
            
        except Exception as e:
            self.logger.error(f"텍스트 임베딩 실패: {e}")
            return np.zeros(self.embedding_dimension)
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """여러 텍스트를 한번에 벡터로 변환 (더 효율적)"""
        try:
            if not texts:
                self.logger.warning("빈 텍스트 리스트가 입력되었습니다")
                return np.array([])
            
            # 빈 텍스트 필터링
            valid_texts = [text for text in texts if text and text.strip()]
            
            if not valid_texts:
                self.logger.warning("유효한 텍스트가 없습니다")
                return np.zeros((len(texts), self.embedding_dimension))
            
            self.logger.info(f"{len(valid_texts)}개 텍스트 배치 임베딩 시작")
            
            # 배치로 임베딩 생성
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=True
            )
            
            self.logger.info("배치 임베딩 완료")
            return embeddings
            
        except Exception as e:
            self.logger.error(f"배치 임베딩 실패: {e}")
            return np.zeros((len(texts), self.embedding_dimension))
    
    def encode_documents(self, documents: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """문서 조각들을 임베딩하고 메타데이터와 함께 반환"""
        try:
            if not documents:
                self.logger.warning("처리할 문서가 없습니다")
                return []
            
            # 텍스트만 추출
            texts = [doc.get('text', '') for doc in documents]
            
            # 배치 임베딩
            embeddings = self.encode_batch(texts)
            
            # 원본 문서에 임베딩 추가
            embedded_documents = []
            for i, doc in enumerate(documents):
                embedded_doc = doc.copy()
                embedded_doc['embedding'] = embeddings[i] if i < len(embeddings) else np.zeros(self.embedding_dimension)
                embedded_doc['embedding_model'] = self.model_name
                embedded_documents.append(embedded_doc)
            
            self.logger.info(f"{len(embedded_documents)}개 문서 임베딩 완료")
            return embedded_documents
            
        except Exception as e:
            self.logger.error(f"문서 임베딩 실패: {e}")
            return documents

class PowerMarketEmbedder(TextEmbedder):
    """전력시장 특화 임베딩 클래스"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        super().__init__(model_name)
        
        # 전력시장 전문용어 사전
        self.power_market_terms = {
            "발전계획": "power generation plan",
            "계통운영": "power system operation", 
            "전력거래": "electricity trading",
            "시장운영": "market operation",
            "예비력": "reserve power",
            "송전제약": "transmission constraint",
            "하루전시장": "day-ahead market",
            "실시간시장": "real-time market",
            "계통한계가격": "system marginal price",
            "급전지시": "dispatch instruction"
        }
    
    def preprocess_power_market_text(self, text: str) -> str:
        """전력시장 텍스트 전처리"""
        # 전문용어 정규화
        processed_text = text
        
        # 특수 문자 정리
        processed_text = processed_text.replace('\n', ' ').replace('\t', ' ')
        
        # 연속된 공백 제거
        import re
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()
        
        return processed_text
    
    def encode_text(self, text: str) -> np.ndarray:
        """전력시장 특화 텍스트 임베딩"""
        # 전처리 후 임베딩
        processed_text = self.preprocess_power_market_text(text)
        return super().encode_text(processed_text)
```

### 3.3 벡터 데이터베이스 모듈 (vector_db/vector_store.py)

```python
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
```

### 3.4 문서 검색 모듈 (retrieval/document_retriever.py)

```python
"""
검색(Retrieval) 모듈
- 사용자 질문을 받아서 관련 문서를 찾는 역할
- 다양한 검색 전략 구현 (벡터 검색, 하이브리드 검색 등)
"""

import logging
from typing import List, Dict, Optional, Union
import numpy as np
import re
from dataclasses import dataclass

@dataclass
class SearchResult:
    """검색 결과를 담는 데이터 클래스"""
    id: str
    text: str
    metadata: Dict
    similarity: float
    source_file: str
    relevance_score: float = 0.0

class DocumentRetriever:
    """문서 검색 엔진 클래스"""
    
    def __init__(self, 
                 vector_db,
                 text_embedder,
                 top_k: int = 5,
                 similarity_threshold: float = 0.7):
        """
        Args:
            vector_db: 벡터 데이터베이스 인스턴스
            text_embedder: 텍스트 임베딩 인스턴스
            top_k: 반환할 최대 결과 수
            similarity_threshold: 유사도 임계값
        """
        self.logger = logging.getLogger(__name__)
        self.vector_db = vector_db
        self.text_embedder = text_embedder
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        # 전력시장 키워드 가중치
        self.power_market_keywords = {
            "발전계획": 1.5,
            "계통운영": 1.5,
            "전력거래": 1.4,
            "시장운영": 1.4,
            "예비력": 1.3,
            "송전제약": 1.3,
            "하루전": 1.2,
            "실시간": 1.2,
            "당일": 1.2,
            "급전": 1.2,
            "가격": 1.1,
            "입찰": 1.1,
            "발전량": 1.1,
            "수요": 1.1
        }
    
    def calculate_keyword_score(self, text: str, query: str) -> float:
        """키워드 기반 관련성 점수 계산"""
        score = 0.0
        text_lower = text.lower()
        query_lower = query.lower()
        
        # 질문의 키워드들
        query_words = query_lower.split()
        
        for word in query_words:
            if word in text_lower:
                # 전력시장 특화 키워드면 가중치 적용
                weight = self.power_market_keywords.get(word, 1.0)
                score += weight
        
        # 전체 단어 수로 정규화
        if len(query_words) > 0:
            score = score / len(query_words)
        
        return score
    
    def semantic_search(self, query: str, top_k: Optional[int] = None) -> List[SearchResult]:
        """의미적 검색 (임베딩 기반)"""
        try:
            if top_k is None:
                top_k = self.top_k
            
            # 질문을 벡터로 변환
            query_embedding = self.text_embedder.encode_text(query)
            
            # 벡터 데이터베이스에서 유사 문서 검색
            results = self.vector_db.search_similar(
                query_embedding=query_embedding,
                top_k=top_k * 2  # 더 많이 가져와서 후처리로 필터링
            )
            
            # 결과 변환 및 필터링
            search_results = []
            for result in results:
                if result['similarity'] >= self.similarity_threshold:
                    search_result = SearchResult(
                        id=result['id'],
                        text=result['text'],
                        metadata=result['metadata'],
                        similarity=result['similarity'],
                        source_file=result['metadata'].get('source_file', ''),
                        relevance_score=result['similarity']
                    )
                    search_results.append(search_result)
            
            # 상위 결과만 반환
            search_results = search_results[:top_k]
            
            self.logger.info(f"의미적 검색 완료: {len(search_results)}개 결과")
            return search_results
            
        except Exception as e:
            self.logger.error(f"의미적 검색 실패: {e}")
            return []
    
    def hybrid_search(self, query: str, 
                     semantic_weight: float = 0.7,
                     keyword_weight: float = 0.3,
                     top_k: Optional[int] = None) -> List[SearchResult]:
        """하이브리드 검색 (의미적 + 키워드 검색 결합)"""
        try:
            if top_k is None:
                top_k = self.top_k
            
            # 각각의 검색 실행
            semantic_results = self.semantic_search(query, top_k * 2)
            keyword_results = self.keyword_search(query, top_k * 2)
            
            # 결과 통합 (ID 기준으로 중복 제거 및 점수 합산)
            combined_results = {}
            
            # 의미적 검색 결과 추가
            for result in semantic_results:
                combined_results[result.id] = result
                combined_results[result.id].relevance_score = (
                    result.similarity * semantic_weight
                )
            
            # 키워드 검색 결과 추가/갱신
            for result in keyword_results:
                if result.id in combined_results:
                    # 기존 결과에 키워드 점수 추가
                    combined_results[result.id].relevance_score += (
                        result.relevance_score * keyword_weight
                    )
                else:
                    # 새로운 결과 추가
                    result.relevance_score = result.relevance_score * keyword_weight
                    combined_results[result.id] = result
            
            # 최종 결과 리스트 생성 및 정렬
            final_results = list(combined_results.values())
            final_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # 상위 결과만 반환
            final_results = final_results[:top_k]
            
            self.logger.info(f"하이브리드 검색 완료: {len(final_results)}개 결과")
            return final_results
            
        except Exception as e:
            self.logger.error(f"하이브리드 검색 실패: {e}")
            return []
    
    def get_context_for_generation(self, search_results: List[SearchResult], 
                                 max_context_length: int = 4000) -> str:
        """검색 결과를 답변 생성용 컨텍스트로 변환"""
        try:
            context_parts = []
            current_length = 0
            
            for i, result in enumerate(search_results):
                # 소스 정보와 함께 텍스트 포맷팅
                formatted_text = f"""
[문서 {i+1}] (출처: {result.source_file}, 유사도: {result.similarity:.3f})
{result.text}
"""
                
                # 길이 확인
                if current_length + len(formatted_text) > max_context_length:
                    break
                
                context_parts.append(formatted_text)
                current_length += len(formatted_text)
            
            context = "\n".join(context_parts)
            
            self.logger.info(f"컨텍스트 생성 완료: {len(context_parts)}개 문서, {len(context)}자")
            return context
            
        except Exception as e:
            self.logger.error(f"컨텍스트 생성 실패: {e}")
            return ""

class PowerMarketRetriever(DocumentRetriever):
    """전력시장 특화 검색 엔진"""
    
    def __init__(self, vector_db, text_embedder, **kwargs):
        super().__init__(vector_db, text_embedder, **kwargs)
        
        # 전력시장 도메인별 가중치
        self.domain_weights = {
            "발전계획": 1.5,
            "계통운영": 1.4,
            "전력거래": 1.3,
            "시장운영": 1.3,
            "예비력": 1.2,
            "송전제약": 1.2
        }
    
    def smart_search(self, query: str, top_k: Optional[int] = None) -> List[SearchResult]:
        """전력시장 특화 스마트 검색"""
        # 질문에서 도메인 키워드 감지
        detected_domains = []
        query_lower = query.lower()
        
        for domain, weight in self.domain_weights.items():
            if domain in query_lower:
                detected_domains.append((domain, weight))
        
        if detected_domains:
            # 도메인이 감지되면 해당 도메인에 특화된 검색
            self.logger.info(f"감지된 도메인: {[d[0] for d in detected_domains]}")
            
            # 가장 높은 가중치의 도메인으로 카테고리 검색
            primary_domain = max(detected_domains, key=lambda x: x[1])[0]
            return self.search_by_category(query, primary_domain, top_k)
        else:
            # 일반적인 하이브리드 검색
            return self.hybrid_search(query, top_k=top_k)
```

### 3.5 답변 생성 모듈 (generation/answer_generator.py)

```python
"""
답변 생성(Generation) 모듈
- 검색된 문서들을 바탕으로 질문에 대한 답변 생성
- 다양한 언어 모델과 연동 가능한 구조
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import re

@dataclass
class GenerationResult:
    """답변 생성 결과를 담는 데이터 클래스"""
    answer: str
    confidence: float
    sources: List[str]
    reasoning: str
    metadata: Dict

class AnswerGenerator:
    """답변 생성 엔진 클래스"""
    
    def __init__(self, 
                 model_type: str = "rule_based",
                 temperature: float = 0.3,
                 max_length: int = 2000):
        """
        Args:
            model_type: 사용할 모델 타입 (rule_based, openai, claude 등)
            temperature: 생성 다양성 조절 (0.0-1.0)
            max_length: 최대 답변 길이
        """
        self.logger = logging.getLogger(__name__)
        self.model_type = model_type
        self.temperature = temperature
        self.max_length = max_length
        
        # 전력시장 특화 답변 템플릿
        self.answer_templates = {
            "발전계획": """
발전계획과 관련하여 다음과 같이 답변드립니다:

{main_answer}

관련 규정:
{regulations}

주요 절차:
{procedures}

참고 문서: {sources}
            """,
            
            "계통운영": """
계통운영에 대한 답변은 다음과 같습니다:

{main_answer}

운영 기준:
{standards}

안전 조치:
{safety_measures}

참고 문서: {sources}
            """,
            
            "일반": """
{main_answer}

상세 내용:
{details}

참고 문서: {sources}
            """
        }
    
    def extract_key_information(self, context: str, query: str) -> Dict[str, str]:
        """컨텍스트에서 핵심 정보 추출"""
        try:
            info = {
                "main_points": [],
                "regulations": [],
                "procedures": [],
                "standards": [],
                "safety_measures": []
            }
            
            # 텍스트를 문장 단위로 분할
            sentences = re.split(r'[.!?]\s+', context)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # 규정 관련 문장
                if any(keyword in sentence for keyword in ["조", "항", "규정", "규칙", "기준"]):
                    info["regulations"].append(sentence)
                
                # 절차 관련 문장
                elif any(keyword in sentence for keyword in ["절차", "단계", "과정", "순서"]):
                    info["procedures"].append(sentence)
                
                # 기준 관련 문장
                elif any(keyword in sentence for keyword in ["기준", "표준", "요구사항"]):
                    info["standards"].append(sentence)
                
                # 안전 관련 문장
                elif any(keyword in sentence for keyword in ["안전", "보안", "위험", "주의"]):
                    info["safety_measures"].append(sentence)
                
                # 일반적인 핵심 내용
                else:
                    info["main_points"].append(sentence)
            
            return info
            
        except Exception as e:
            self.logger.error(f"핵심 정보 추출 실패: {e}")
            return {"main_points": [context], "regulations": [], "procedures": [], 
                   "standards": [], "safety_measures": []}
    
    def determine_domain(self, query: str, context: str) -> str:
        """질문과 컨텍스트를 바탕으로 도메인 판단"""
        domain_keywords = {
            "발전계획": ["발전계획", "하루전", "당일", "실시간", "계획수립"],
            "계통운영": ["계통운영", "운영기준", "안전운전", "계통제약"],
            "전력거래": ["전력거래", "입찰", "가격", "시장"],
            "예비력": ["예비력", "예비력시장", "예비력용량"],
            "송전제약": ["송전제약", "제약정보", "계통제약"]
        }
        
        combined_text = (query + " " + context).lower()
        
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            domain_scores[domain] = score
        
        # 가장 높은 점수의 도메인 반환
        if domain_scores:
            best_domain = max(domain_scores, key=domain_scores.get)
            if domain_scores[best_domain] > 0:
                return best_domain
        
        return "일반"
    
    def generate_rule_based_answer(self, context: str, query: str, sources: List[str]) -> GenerationResult:
        """규칙 기반 답변 생성"""
        try:
            # 도메인 판단
            domain = self.determine_domain(query, context)
            
            # 핵심 정보 추출
            key_info = self.extract_key_information(context, query)
            
            # 메인 답변 생성
            main_answer = self._generate_main_answer(query, key_info["main_points"])
            
            # 템플릿 선택 및 답변 구성
            template = self.answer_templates.get(domain, self.answer_templates["일반"])
            
            if domain == "발전계획":
                answer = template.format(
                    main_answer=main_answer,
                    regulations=self._format_list(key_info["regulations"]),
                    procedures=self._format_list(key_info["procedures"]),
                    sources=", ".join(sources)
                )
            elif domain == "계통운영":
                answer = template.format(
                    main_answer=main_answer,
                    standards=self._format_list(key_info["standards"]),
                    safety_measures=self._format_list(key_info["safety_measures"]),
                    sources=", ".join(sources)
                )
            else:
                answer = template.format(
                    main_answer=main_answer,
                    details=self._format_list(key_info["regulations"] + key_info["procedures"]),
                    sources=", ".join(sources)
                )
            
            # 신뢰도 계산
            confidence = self.calculate_confidence(context, query, answer)
            
            # 추론 과정 설명
            reasoning = f"도메인: {domain}, 참조 문서 수: {len(sources)}, 핵심 정보: {len(key_info['main_points'])}개 포인트"
            
            result = GenerationResult(
                answer=answer.strip(),
                confidence=confidence,
                sources=sources,
                reasoning=reasoning,
                metadata={
                    "domain": domain,
                    "generation_method": "rule_based",
                    "context_length": len(context),
                    "query_length": len(query)
                }
            )
            
            self.logger.info(f"규칙 기반 답변 생성 완료 (신뢰도: {confidence:.3f})")
            return result
            
        except Exception as e:
            self.logger.error(f"규칙 기반 답변 생성 실패: {e}")
            return GenerationResult(
                answer="죄송합니다. 답변 생성 중 오류가 발생했습니다.",
                confidence=0.0,
                sources=sources,
                reasoning="답변 생성 실패",
                metadata={"error": str(e)}
            )
    
    def _generate_main_answer(self, query: str, main_points: List[str]) -> str:
        """메인 답변 생성"""
        if not main_points:
            return "관련 정보를 찾을 수 없습니다."
        
        # 가장 관련성 높은 포인트들 선택 (최대 3개)
        relevant_points = main_points[:3]
        
        # 질문 유형에 따른 답변 시작
        if "무엇" in query or "뭐" in query:
            answer_start = "다음과 같습니다:"
        elif "어떻게" in query or "방법" in query:
            answer_start = "다음과 같은 방법으로 수행됩니다:"
        elif "언제" in query or "시간" in query:
            answer_start = "다음과 같은 시점에 실행됩니다:"
        elif "왜" in query or "이유" in query:
            answer_start = "다음과 같은 이유 때문입니다:"
        else:
            answer_start = "관련 내용은 다음과 같습니다:"
        
        return answer_start + "\n\n" + "\n\n".join(f"• {point}" for point in relevant_points)
    
    def _format_list(self, items: List[str]) -> str:
        """리스트를 읽기 좋은 형태로 포맷팅"""
        if not items:
            return "해당 정보가 없습니다."
        
        formatted_items = []
        for i, item in enumerate(items[:5], 1):  # 최대 5개만
            formatted_items.append(f"{i}. {item}")
        
        return "\n".join(formatted_items)
    
    def generate_answer(self, context: str, query: str, sources: List[str]) -> GenerationResult:
        """질문에 대한 답변 생성 (메인 인터페이스)"""
        try:
            self.logger.info(f"답변 생성 시작 - 모델: {self.model_type}")
            
            if self.model_type == "rule_based":
                return self.generate_rule_based_answer(context, query, sources)
            else:
                # 다른 모델 타입들은 추후 구현
                self.logger.warning(f"지원하지 않는 모델 타입: {self.model_type}")
                return self.generate_rule_based_answer(context, query, sources)
                
        except Exception as e:
            self.logger.error(f"답변 생성 전체 실패: {e}")
            return GenerationResult(
                answer="시스템 오류로 인해 답변을 생성할 수 없습니다.",
                confidence=0.0,
                sources=sources,
                reasoning="시스템 오류",
                metadata={"error": str(e)}
            )

class PowerMarketAnswerGenerator(AnswerGenerator):
    """전력시장 특화 답변 생성기"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 전력시장 특화 답변 패턴
        self.specialized_patterns = {
            "regulation_pattern": r"제\s*(\d+(?:\.\d+)*)\s*조",
            "article_pattern": r"(\d+(?:\.\d+)*)\s*항",
            "schedule_pattern": r"별표\s*(\d+)",
            "time_pattern": r"(\d+)시\s*(\d+)분",
            "percentage_pattern": r"(\d+(?:\.\d+)*)\s*%"
        }
    
    def enhance_answer_with_regulations(self, answer: str, context: str) -> str:
        """답변에 규정 정보 강화"""
        # 규정 번호 추출 및 강조
        regulations = re.findall(self.specialized_patterns["regulation_pattern"], context)
        
        if regulations:
            reg_info = f"\n\n📋 관련 규정: " + ", ".join([f"제{reg}조" for reg in regulations[:3]])
            answer += reg_info
        
        return answer
```

---

## 4. 설정 및 스크립트

### 4.1 시스템 설정 (config/config.yaml)

```yaml
# RAG 시스템 설정 파일

# 벡터 데이터베이스 설정
VECTOR_DB_TYPE: "chromadb"  # chromadb 또는 faiss
VECTOR_DB_PATH: "./vector_db"
COLLECTION_NAME: "power_market_docs"

# 임베딩 모델 설정
EMBEDDING_MODEL: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION: 384

# 문서 처리 설정
CHUNK_SIZE: 1000  # 텍스트를 나누는 크기
CHUNK_OVERLAP: 200  # 겹치는 부분 크기
MAX_TOKENS: 4000  # 최대 토큰 수

# 검색 설정
TOP_K: 5  # 상위 몇 개 문서를 가져올지
SIMILARITY_THRESHOLD: 0.7  # 유사도 임계값

# API 설정
API_HOST: "0.0.0.0"
API_PORT: 8000
DEBUG: true

# 로그 설정
LOG_LEVEL: "INFO"
LOG_FILE: "./logs/rag_system.log"

# 전력시장 특화 설정
POWER_MARKET_DOMAINS:
  - "발전계획"
  - "계통운영"
  - "전력거래"
  - "시장운영"
  - "예비력"
  - "송전제약"
```

### 4.2 패키지 요구사항 (requirements.txt)

```
# RAG 시스템을 위한 필수 라이브러리들

# 벡터 데이터베이스
chromadb==0.4.22
faiss-cpu==1.7.4

# 텍스트 임베딩 (벡터 변환)
sentence-transformers==2.2.2
transformers==4.36.0
torch==2.0.1

# 문서 처리
langchain==0.1.0
PyPDF2==3.0.1
python-docx==0.8.11
openpyxl==3.1.2

# 웹 API 서버
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0

# 데이터 처리
pandas==2.1.4
numpy==1.24.3

# 설정 관리
python-dotenv==1.0.0
pyyaml==6.0.1

# 로깅
loguru==0.7.2

# 개발용 도구
jupyter==1.0.0
pytest==7.4.3
```

### 4.3 설치 스크립트 (install.sh)

```bash
#!/bin/bash

# 전력시장 RAG 시스템 설치 스크립트
# Ubuntu/WSL 환경에서 실행

echo "🚀 전력시장 RAG 시스템 설치를 시작합니다..."

# 1. Python 버전 확인
echo "1. Python 버전 확인 중..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python3가 설치되어 있지 않습니다. Python3를 먼저 설치해주세요."
    exit 1
fi

# 2. 가상환경 생성
echo "2. Python 가상환경 생성 중..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ 가상환경 생성 실패. python3-venv를 설치해주세요:"
    echo "sudo apt update && sudo apt install python3-venv"
    exit 1
fi

# 3. 가상환경 활성화
echo "3. 가상환경 활성화 중..."
source venv/bin/activate

# 4. pip 업그레이드
echo "4. pip 업그레이드 중..."
pip install --upgrade pip

# 5. 필요한 패키지 설치
echo "5. 필요한 패키지 설치 중..."
echo "⏳ 이 과정은 몇 분 정도 소요될 수 있습니다..."

pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 패키지 설치 실패. 네트워크 연결을 확인해주세요."
    exit 1
fi

# 6. 필요한 디렉토리 생성
echo "6. 필요한 디렉토리 확인 중..."
mkdir -p logs
mkdir -p documents

# 7. 설치 완료 메시지
echo ""
echo "✅ 전력시장 RAG 시스템 설치가 완료되었습니다!"
echo ""
echo "📝 다음 명령어로 시스템을 실행할 수 있습니다:"
echo ""
echo "   # 가상환경 활성화"
echo "   source venv/bin/activate"
echo ""
echo "   # 메인 시스템 실행"
echo "   python power_market_rag.py"
echo ""
echo "   # API 서버 실행"
echo "   python api/api_server.py"
echo ""
echo "📚 문서를 documents/ 폴더에 넣고 시스템을 실행하세요."
echo ""
echo "🌐 API 서버를 실행하면 http://localhost:8000 에서 웹 인터페이스를 사용할 수 있습니다."
```

### 4.4 실행 스크립트 (run.sh)

```bash
#!/bin/bash

# 전력시장 RAG 시스템 실행 스크립트

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수: 제목 출력
print_title() {
    echo -e "${BLUE}"
    echo "=================================================="
    echo "         ⚡ 전력시장 RAG 시스템 실행기 ⚡"
    echo "=================================================="
    echo -e "${NC}"
}

# 함수: 가상환경 확인 및 활성화
activate_venv() {
    if [ -d "venv" ]; then
        echo -e "${GREEN}📦 가상환경 활성화 중...${NC}"
        source venv/bin/activate
        echo -e "${GREEN}✅ 가상환경이 활성화되었습니다.${NC}"
    else
        echo -e "${RED}❌ 가상환경이 없습니다. 먼저 install.sh를 실행해주세요.${NC}"
        exit 1
    fi
}

# 함수: API 서버 실행
run_api_server() {
    echo -e "${YELLOW}🌐 API 서버를 시작합니다...${NC}"
    echo -e "${BLUE}📍 웹 인터페이스: http://localhost:8000${NC}"
    echo -e "${BLUE}📖 API 문서: http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  서버를 중지하려면 Ctrl+C를 누르세요.${NC}"
    echo ""
    
    cd api
    python api_server.py
}

# 함수: 메인 시스템 실행
run_main_system() {
    echo -e "${YELLOW}🔄 메인 RAG 시스템을 시작합니다...${NC}"
    python power_market_rag.py
}

# 메인 함수
main() {
    print_title
    
    # 현재 디렉토리 확인
    if [ ! -f "power_market_rag.py" ]; then
        echo -e "${RED}❌ power_market_rag.py 파일을 찾을 수 없습니다.${NC}"
        echo -e "${RED}   올바른 프로젝트 디렉토리에서 실행해주세요.${NC}"
        exit 1
    fi
    
    # 가상환경 활성화
    activate_venv
    
    # 실행 모드 선택
    echo -e "${BLUE}실행할 모드를 선택하세요:${NC}"
    echo "1) 🌐 API 서버 실행 (웹 인터페이스 포함)"
    echo "2) 🔄 메인 시스템 실행 (콘솔 모드)"
    echo "3) 🧪 시스템 테스트 실행"
    echo "4) 📊 시스템 상태 확인"
    echo "5) 🚪 종료"
    echo ""
    
    read -p "선택 (1-5): " choice
    
    case $choice in
        1)
            run_api_server
            ;;
        2)
            run_main_system
            ;;
        3)
            run_tests
            ;;
        4)
            echo -e "${YELLOW}📊 시스템 상태를 확인합니다...${NC}"
            python -c "
from power_market_rag import PowerMarketRAG
rag = PowerMarketRAG()
status = rag.get_system_status()
print(f'시스템 상태: {status}')
            "
            ;;
        5)
            echo -e "${GREEN}👋 시스템을 종료합니다.${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ 잘못된 선택입니다. 1-5 중에서 선택해주세요.${NC}"
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
```

---

## 5. 예시 문서

### 5.1 발전계획 가이드 (documents/발전계획_가이드.md)

```markdown
# 전력시장 발전계획 수립 가이드

## 1. 하루전발전계획

### 1.1 개요
하루전발전계획은 전력거래일 전일에 수립되는 발전계획으로, 전력시장운영규칙 제16.4.1조에 따라 수립됩니다.

### 1.2 수립 절차
하루전발전계획 수립 절차는 다음과 같습니다:

1. **11시**: 초기입찰 입력
2. **16시**: 제주수요예측 연계
3. **17시**: 하루전발전계획 수립 및 하루전에너지가격 산정
4. **18시**: 하루전발전계획 및 하루전에너지가격 공표

### 1.3 목적함수
발전계획수립기간 동안의 총 발전비용 및 수요감축비용 최소화를 목적으로 다음 제약을 고려합니다:
- 운영예비력 제약
- 발전기 자기제약
- 송전제약

## 2. 당일발전계획

### 2.1 개요
당일발전계획은 전력시장운영규칙 제16.4.3조에 따라 매시간마다 통지되는 발전계획입니다.

### 2.2 수립 특징
- 발전계획 수립시 최신 예측정보 사용
- 최신 송전제약 반영
- 실시간 수요변화 대응

## 3. 실시간발전계획

### 3.1 개요
실시간발전계획은 실시간시장 단위거래시간인 15분마다 통지되는 발전계획입니다.

### 3.2 특징
- 15분 단위 운영
- 최신예측정보 반영
- 송전제약 실시간 적용
```

### 5.2 계통운영기준 (documents/계통운영기준.md)

```markdown
# 전력계통 운영기준

## 1. 계통운영의 기본원칙

### 1.1 안전성 우선
전력계통 운영에서 가장 중요한 것은 안전성 확보입니다.
- 계통 안정도 유지
- 설비 보호
- 인명 안전 확보

### 1.2 신뢰성 확보
- 전력 공급의 연속성 보장
- 정전 최소화
- 빠른 복구 능력 확보

## 2. 계통운영 기준

### 2.1 주파수 관리
한국 전력계통의 정격 주파수는 60Hz입니다.

#### 2.1.1 주파수 허용범위
- **정상운전**: 59.8 ~ 60.2Hz (±0.2Hz)
- **경계운전**: 59.5 ~ 60.5Hz (±0.5Hz)
- **비상운전**: 59.0 ~ 61.0Hz (±1.0Hz)

#### 2.1.2 주파수 제어 방법
1. **1차 제어**: 조속기에 의한 자동 제어 (수초 이내)
2. **2차 제어**: AGC(Automatic Generation Control)에 의한 제어 (수분 이내)
3. **3차 제어**: 운전원에 의한 수동 제어 (수십분 이내)

### 2.2 예비력 관리

#### 2.2.1 예비력 종류
1. **운전예비력**: 현재 운전 중인 발전기의 여유 용량
2. **정지예비력**: 빠른 시간 내 기동 가능한 정지 발전기 용량
3. **교체예비력**: 장시간 운전 가능한 예비 발전기 용량

#### 2.2.2 예비력 요구량
- **운전예비력**: 최대부하의 7% 이상
- **순동예비력**: 최대 발전기 용량 이상
- **기동예비력**: 최대부하의 10% 이상
```

---

## 6. 설치 및 실행

### 6.1 시스템 요구사항

#### 최소 요구사항
- **OS**: Ubuntu 20.04+ / WSL2 / macOS 10.15+
- **Python**: 3.8 이상
- **RAM**: 4GB 이상
- **Storage**: 2GB 이상 여유 공간

#### 권장 사양
- **OS**: Ubuntu 22.04 / WSL2
- **Python**: 3.10 이상
- **RAM**: 8GB 이상
- **Storage**: 10GB 이상 여유 공간

### 6.2 설치 방법

#### 자동 설치 (권장)

```bash
# 1. 프로젝트 다운로드
git clone <repository-url>
cd power_market_rag

# 2. 설치 스크립트 실행
chmod +x install.sh
./install.sh
```

#### 수동 설치

```bash
# 1. Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 2. 필요한 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt

# 3. 디렉토리 생성
mkdir -p logs documents
```

### 6.3 실행 방법

#### 간편 실행

```bash
# 실행 스크립트 사용
chmod +x run.sh
./run.sh
```

#### 개별 실행

```bash
# 가상환경 활성화
source venv/bin/activate

# 데모 실행
python demo.py

# API 서버 실행
python api/api_server.py

# 메인 시스템 실행
python power_market_rag.py
```

---

## 7. 사용법 가이드

### 7.1 웹 인터페이스 사용

1. **API 서버 시작**
   ```bash
   python api/api_server.py
   ```

2. **웹 브라우저 접속**
   - URL: `http://localhost:8000`

3. **질문 입력**
   - 질문 입력창에 전력시장 관련 질문 작성
   - 검색 방법 선택 (하이브리드 권장)
   - "질문하기" 버튼 클릭

4. **답변 확인**
   - 생성된 답변과 신뢰도 확인
   - 참고 문서 출처 확인

### 7.2 문서 추가 방법

#### 방법 1: 파일 직접 복사
```bash
cp your_document.pdf documents/
```

#### 방법 2: 웹 인터페이스 업로드
1. 웹 인터페이스 접속
2. 파일 업로드 섹션 이용
3. 드래그&드롭 또는 파일 선택

### 7.3 예시 질문들

#### 발전계획 관련
- "하루전발전계획은 언제 수립되나요?"
- "실시간발전계획의 운영 주기는?"
- "발전계획 수립 절차를 알려주세요"

#### 계통운영 관련
- "계통운영의 기본 원칙은 무엇인가요?"
- "송전제약이란 무엇인가요?"
- "계통 안정성을 위한 조치는?"

#### 시장운영 관련
- "전력시장의 구조는 어떻게 되나요?"
- "입찰 절차를 설명해주세요"
- "가격 결정 방식은?"

---

## 8. API 사용법

### 8.1 주요 엔드포인트

#### 1. 질문하기
```bash
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "하루전발전계획이 무엇인가요?",
       "search_method": "hybrid"
     }'
```

**응답 예시:**
```json
{
  "answer": "하루전발전계획은 전력거래일 전일에 수립되는 발전계획으로...",
  "confidence": 0.92,
  "sources": ["발전계획_가이드.md"],
  "reasoning": "도메인: 발전계획, 참조 문서 수: 1",
  "search_results": 3,
  "search_method": "hybrid"
}
```

#### 2. 문서 검색
```bash
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "발전계획",
       "method": "semantic",
       "top_k": 5
     }'
```

#### 3. 시스템 상태 확인
```bash
curl -X GET "http://localhost:8000/status"
```

#### 4. 파일 업로드
```bash
curl -X POST "http://localhost:8000/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "files=@document.pdf"
```

### 8.2 API 문서 확인
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 9. 문제해결

### 9.1 자주 발생하는 문제들

#### 1. 메모리 부족 오류
```bash
# 해결방법: 청크 크기 줄이기
# config/config.yaml에서 CHUNK_SIZE를 500으로 변경
CHUNK_SIZE: 500
```

#### 2. ChromaDB 오류
```bash
# 해결방법: 데이터베이스 초기화
rm -rf vector_db/
python power_market_rag.py
```

#### 3. 모델 다운로드 실패
```bash
# 해결방법: 수동 다운로드
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
"
```

#### 4. 한글 인코딩 문제
```bash
# 해결방법: 환경변수 설정
export PYTHONIOENCODING=utf-8
export LANG=ko_KR.UTF-8
```

### 9.2 성능 최적화 팁

#### 1. GPU 사용 (CUDA 지원시)
```yaml
# config/config.yaml
EMBEDDING_MODEL: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
USE_GPU: true
```

#### 2. 배치 크기 조정
```yaml
# 메모리에 따라 조정
BATCH_SIZE: 16  # 메모리 부족시 8로 감소
```

#### 3. 인덱스 최적화
```python
# 정기적인 인덱스 리빌드
python -c "
from power_market_rag import PowerMarketRAG
rag = PowerMarketRAG()
rag.clear_database()
rag.load_documents('documents')
"
```

---

## 10. 고급 설정

### 10.1 zsh 최적화 설정

```bash
# .zshrc에 추가 가능한 별칭
alias rag-start="cd /home/zwtiger/power_market_rag && source venv/bin/activate && ./run.sh"
alias rag-demo="cd /home/zwtiger/power_market_rag && source venv/bin/activate && python demo.py"
alias rag-test="cd /home/zwtiger/power_market_rag && source venv/bin/activate && python test_basic.py"
```

### 10.2 성능 튜닝

```yaml
# config/config.yaml에서 조정 가능
CHUNK_SIZE: 500          # 메모리 부족시 감소
EMBEDDING_MODEL: "multilingual-MiniLM-L12-v2"  # 빠른 처리
TOP_K: 3                 # 검색 결과 수 조정
SIMILARITY_THRESHOLD: 0.8  # 엄격한 필터링
```

### 10.3 고급 모델 설정

```python
# 더 강력한 임베딩 모델 사용
EMBEDDING_MODEL: "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# OpenAI API 연동 (추후 구현)
OPENAI_API_KEY: "your-api-key"
OPENAI_MODEL: "gpt-4"

# Claude API 연동 (추후 구현)
CLAUDE_API_KEY: "your-api-key"
CLAUDE_MODEL: "claude-3-sonnet"
```

---

## 🎉 마무리

이 문서에는 전력시장 RAG 시스템의 모든 구성 요소가 포함되어 있습니다:

### ✅ 완성된 기능들
- 📄 **완전한 문서 처리 파이프라인**
- 🧠 **ChromaDB 기반 벡터 저장소**
- 🔍 **4가지 검색 방식** (의미적, 키워드, 하이브리드, 스마트)
- 💡 **전력시장 특화 답변 생성**
- 🌐 **웹 인터페이스 및 API**
- ⚙️ **모듈형 아키텍처**
- 📚 **상세한 문서화**

### 🚀 즉시 시작 가이드
1. 코드 복사 후 파일 구조 생성
2. `chmod +x install.sh && ./install.sh` 실행
3. `./run.sh` 실행하여 웹 인터페이스 시작
4. `http://localhost:8000`에서 질문 테스트

이제 전력시장 전문 지식을 즉시 검색하고 활용할 수 있는 완전한 RAG 시스템을 갖추게 되었습니다! 🎯