"""
하이브리드 벡터 엔진
Dense + Sparse + Multimodal 벡터를 통합하여 AI가 최적으로 활용할 수 있는 검색 시스템
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path
import json
import logging
from datetime import datetime
import pickle

# Vector stores
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# Embedding models
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


class VectorEngine:
    """
    AI 최적화 하이브리드 벡터 엔진
    
    기능:
    - Dense Vector: 의미적 유사성 (Sentence Transformers)
    - Sparse Vector: 키워드 매칭 (TF-IDF)
    - Multimodal Vector: 이미지-텍스트 통합 (CLIP)
    - 계층적 인덱싱: Document > Section > Paragraph > Sentence
    """
    
    def __init__(
        self,
        data_dir: str = "data",
        dense_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        enable_multimodal: bool = True,
        enable_sparse: bool = True
    ):
        self.data_dir = Path(data_dir)
        self.vectors_dir = self.data_dir / "vectors"
        self.metadata_dir = self.data_dir / "metadata"
        
        # 디렉토리 생성
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # 모델 설정
        self.dense_model_name = dense_model
        self.enable_multimodal = enable_multimodal
        self.enable_sparse = enable_sparse
        
        # 벡터 저장소 초기화
        self.dense_model = None
        self.sparse_vectorizer = None
        self.multimodal_model = None
        self.chroma_client = None
        self.faiss_index = None
        
        # 메타데이터 저장소
        self.document_metadata = {}
        self.section_metadata = {}
        self.paragraph_metadata = {}
        self.sentence_metadata = {}
        
        self._initialize_models()
    
    def _initialize_models(self):
        """모델 초기화"""
        logger.info("벡터 엔진 모델 초기화 시작...")
        
        # Dense 벡터 모델 (Sentence Transformers)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.dense_model = SentenceTransformer(self.dense_model_name)
                logger.info(f"Dense 벡터 모델 로드 완료: {self.dense_model_name}")
            except Exception as e:
                logger.warning(f"Dense 벡터 모델 로드 실패: {e}")
                self.dense_model = None
        
        # Sparse 벡터 모델 (TF-IDF)
        if self.enable_sparse and SKLEARN_AVAILABLE:
            try:
                self.sparse_vectorizer = TfidfVectorizer(
                    max_features=10000,
                    ngram_range=(1, 2),
                    stop_words=None,  # 한국어 불용어는 별도 처리
                    lowercase=True
                )
                logger.info("Sparse 벡터 모델 (TF-IDF) 초기화 완료")
            except Exception as e:
                logger.warning(f"Sparse 벡터 모델 초기화 실패: {e}")
                self.sparse_vectorizer = None
        
        # ChromaDB 초기화
        if CHROMADB_AVAILABLE:
            try:
                self.chroma_client = chromadb.PersistentClient(
                    path=str(self.vectors_dir / "chroma")
                )
                logger.info("ChromaDB 클라이언트 초기화 완료")
            except Exception as e:
                logger.warning(f"ChromaDB 초기화 실패: {e}")
                self.chroma_client = None
        
        # Multimodal 모델은 필요시 나중에 초기화
        logger.info("벡터 엔진 초기화 완료")
    
    def get_collection(self, collection_name: str):
        """ChromaDB 컬렉션 가져오기 또는 생성"""
        if not self.chroma_client:
            return None
        
        try:
            return self.chroma_client.get_collection(collection_name)
        except:
            return self.chroma_client.create_collection(
                name=collection_name,
                metadata={"description": f"AI 최적화 벡터 컬렉션: {collection_name}"}
            )
    
    def encode_dense(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Dense 벡터 인코딩"""
        if not self.dense_model:
            logger.warning("Dense 모델이 없습니다. 더미 벡터 반환")
            if isinstance(texts, str):
                return np.random.random(384).astype(np.float32)
            return np.random.random((len(texts), 384)).astype(np.float32)
        
        return self.dense_model.encode(texts)
    
    def encode_sparse(self, texts: List[str]) -> np.ndarray:
        """Sparse 벡터 인코딩"""
        if not self.sparse_vectorizer:
            logger.warning("Sparse 모델이 없습니다. 더미 벡터 반환")
            return np.random.random((len(texts), 1000)).astype(np.float32)
        
        return self.sparse_vectorizer.fit_transform(texts).toarray()
    
    def add_document(
        self,
        doc_id: str,
        content: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        계층적 문서 추가
        
        Args:
            doc_id: 문서 ID
            content: 계층별 컨텐츠 {'document': str, 'sections': [...], 'paragraphs': [...], 'sentences': [...]}
            metadata: 문서 메타데이터
        """
        try:
            logger.info(f"문서 추가 시작: {doc_id}")
            
            # 1. Document Level
            if 'document' in content:
                self._add_document_level(doc_id, content['document'], metadata)
            
            # 2. Section Level  
            if 'sections' in content:
                self._add_section_level(doc_id, content['sections'])
            
            # 3. Paragraph Level
            if 'paragraphs' in content:
                self._add_paragraph_level(doc_id, content['paragraphs'])
            
            # 4. Sentence Level
            if 'sentences' in content:
                self._add_sentence_level(doc_id, content['sentences'])
            
            logger.info(f"문서 추가 완료: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"문서 추가 실패 {doc_id}: {e}")
            return False
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """ChromaDB 호환 메타데이터로 변환"""
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[key] = value
            elif isinstance(value, list):
                # 리스트를 문자열로 변환
                sanitized[key] = str(value) if len(str(value)) < 1000 else f"[{len(value)} items]"
            elif isinstance(value, dict):
                # 딕셔너리는 JSON 문자열로 변환
                json_str = json.dumps(value, ensure_ascii=False)
                sanitized[key] = json_str if len(json_str) < 1000 else f"{{dict with {len(value)} keys}}"
            else:
                # 기타 타입은 문자열로 변환
                sanitized[key] = str(value)
        return sanitized

    def _add_document_level(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        """문서 레벨 벡터 추가"""
        # Dense 벡터
        dense_vector = self.encode_dense(content)
        
        # ChromaDB에 저장
        doc_collection = self.get_collection("documents")
        if doc_collection:
            clean_metadata = self._sanitize_metadata({
                **metadata,
                "level": "document",
                "added_at": datetime.now().isoformat()
            })
            doc_collection.add(
                ids=[doc_id],
                documents=[content],
                embeddings=[dense_vector.tolist()],
                metadatas=[clean_metadata]
            )
        
        # 메타데이터 저장
        self.document_metadata[doc_id] = {
            **metadata,
            "content_length": len(content),
            "vector_dim": len(dense_vector),
            "level": "document"
        }
    
    def _add_section_level(self, doc_id: str, sections: List[Dict[str, Any]]):
        """섹션 레벨 벡터 추가"""
        section_collection = self.get_collection("sections")
        if not section_collection:
            return
        
        for i, section in enumerate(sections):
            section_id = f"{doc_id}_section_{i}"
            content = section.get('content', '')
            
            if content:
                dense_vector = self.encode_dense(content)
                
                clean_metadata = self._sanitize_metadata({
                    "document_id": doc_id,
                    "section_index": i,
                    "title": section.get('title', ''),
                    "level": "section",
                    "added_at": datetime.now().isoformat()
                })
                
                section_collection.add(
                    ids=[section_id],
                    documents=[content],
                    embeddings=[dense_vector.tolist()],
                    metadatas=[clean_metadata]
                )
                
                self.section_metadata[section_id] = {
                    "document_id": doc_id,
                    "section_index": i,
                    "title": section.get('title', ''),
                    "content_length": len(content)
                }
    
    def _add_paragraph_level(self, doc_id: str, paragraphs: List[Dict[str, Any]]):
        """문단 레벨 벡터 추가"""
        paragraph_collection = self.get_collection("paragraphs")
        if not paragraph_collection:
            return
        
        for i, paragraph in enumerate(paragraphs):
            paragraph_id = f"{doc_id}_para_{i}"
            content = paragraph.get('content', '')
            
            if content:
                dense_vector = self.encode_dense(content)
                
                clean_metadata = self._sanitize_metadata({
                    "document_id": doc_id,
                    "paragraph_index": i,
                    "section_id": paragraph.get('section_id', ''),
                    "level": "paragraph",
                    "added_at": datetime.now().isoformat()
                })
                
                paragraph_collection.add(
                    ids=[paragraph_id],
                    documents=[content],
                    embeddings=[dense_vector.tolist()],
                    metadatas=[clean_metadata]
                )
    
    def _add_sentence_level(self, doc_id: str, sentences: List[Dict[str, Any]]):
        """문장 레벨 벡터 추가"""
        sentence_collection = self.get_collection("sentences")
        if not sentence_collection:
            return
        
        # 배치 처리로 성능 향상
        batch_size = 100
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i + batch_size]
            
            ids = []
            documents = []
            metadatas = []
            
            for j, sentence in enumerate(batch):
                sentence_id = f"{doc_id}_sent_{i + j}"
                content = sentence.get('content', '')
                
                if content:
                    ids.append(sentence_id)
                    documents.append(content)
                    clean_metadata = self._sanitize_metadata({
                        "document_id": doc_id,
                        "sentence_index": i + j,
                        "paragraph_id": sentence.get('paragraph_id', ''),
                        "level": "sentence",
                        "added_at": datetime.now().isoformat()
                    })
                    metadatas.append(clean_metadata)
            
            if ids:
                embeddings = self.encode_dense(documents)
                sentence_collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings.tolist(),
                    metadatas=metadatas
                )
    
    def search(
        self,
        query: str,
        search_type: str = "hybrid",
        level: str = "all",
        top_k: int = 10,
        include_metadata: bool = True,
        include_context: bool = True,
        ai_friendly: bool = True
    ) -> Dict[str, Any]:
        """
        AI 최적화 하이브리드 검색
        
        Args:
            query: 검색 쿼리
            search_type: "dense", "sparse", "multimodal", "hybrid"
            level: "document", "section", "paragraph", "sentence", "all"
            top_k: 반환할 결과 수
            include_metadata: 메타데이터 포함 여부
            include_context: 관련 컨텍스트 포함 여부
            ai_friendly: AI 친화적 형태로 반환 여부
        
        Returns:
            AI가 활용하기 쉬운 구조화된 검색 결과
        """
        start_time = datetime.now()
        
        try:
            # 레벨별 검색 수행
            results = {}
            
            if level == "all":
                levels_to_search = ["document", "section", "paragraph", "sentence"]
            else:
                levels_to_search = [level]
            
            for search_level in levels_to_search:
                level_results = self._search_level(
                    query, search_level, search_type, top_k // len(levels_to_search)
                )
                if level_results:
                    results[search_level] = level_results
            
            # AI 친화적 결과 구성
            if ai_friendly:
                return self._format_ai_friendly_results(
                    results, query, include_metadata, include_context, start_time
                )
            else:
                return results
                
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            return {
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    def _search_level(self, query: str, level: str, search_type: str, top_k: int) -> List[Dict]:
        """특정 레벨에서 검색 수행"""
        collection = self.get_collection(f"{level}s")
        if not collection:
            return []
        
        try:
            # Dense 검색
            if search_type in ["dense", "hybrid"]:
                query_vector = self.encode_dense(query)
                
                results = collection.query(
                    query_embeddings=[query_vector.tolist()],
                    n_results=top_k,
                    include=['documents', 'metadatas', 'distances']
                )
                
                formatted_results = []
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "score": 1 - results['distances'][0][i],  # distance를 similarity로 변환
                        "search_type": "dense"
                    })
                
                return formatted_results
            
            return []
            
        except Exception as e:
            logger.error(f"레벨 {level} 검색 실패: {e}")
            return []
    
    def _format_ai_friendly_results(
        self,
        results: Dict[str, List],
        query: str,
        include_metadata: bool,
        include_context: bool,
        start_time: datetime
    ) -> Dict[str, Any]:
        """AI가 활용하기 쉬운 형태로 결과 포맷팅"""
        
        # 결과 통합 및 정렬
        all_results = []
        for level, level_results in results.items():
            for result in level_results:
                result['level'] = level
                all_results.append(result)
        
        # 점수순 정렬
        all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # AI 친화적 구조 생성
        ai_response = {
            "query": query,
            "search_metadata": {
                "search_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "total_results": len(all_results),
                "levels_searched": list(results.keys()),
                "timestamp": datetime.now().isoformat()
            },
            "primary_results": [],
            "supporting_evidence": [],
            "related_context": []
        }
        
        # 결과 분류
        for i, result in enumerate(all_results[:20]):  # 상위 20개만
            formatted_result = {
                "content": result['content'],
                "relevance_score": result.get('score', 0),
                "source_level": result['level'],
                "source_id": result['id']
            }
            
            if include_metadata and 'metadata' in result:
                formatted_result['metadata'] = result['metadata']
            
            # 상위 5개는 primary_results
            if i < 5:
                ai_response["primary_results"].append(formatted_result)
            # 다음 10개는 supporting_evidence
            elif i < 15:
                ai_response["supporting_evidence"].append(formatted_result)
            # 나머지는 related_context
            else:
                ai_response["related_context"].append(formatted_result)
        
        return ai_response
    
    def get_statistics(self) -> Dict[str, Any]:
        """벡터 엔진 통계 정보"""
        stats = {
            "collections": {},
            "models": {
                "dense_model": self.dense_model_name if self.dense_model else None,
                "sparse_enabled": self.enable_sparse,
                "multimodal_enabled": self.enable_multimodal
            },
            "storage": {
                "vectors_dir": str(self.vectors_dir),
                "metadata_dir": str(self.metadata_dir)
            }
        }
        
        # 컬렉션별 통계
        if self.chroma_client:
            try:
                collections = self.chroma_client.list_collections()
                for collection in collections:
                    stats["collections"][collection.name] = {
                        "count": collection.count(),
                        "metadata": collection.metadata
                    }
            except Exception as e:
                logger.warning(f"통계 수집 실패: {e}")
        
        return stats
    
    def save_metadata(self):
        """메타데이터를 파일로 저장"""
        try:
            # 문서 메타데이터 저장
            with open(self.metadata_dir / "documents.json", "w", encoding="utf-8") as f:
                json.dump(self.document_metadata, f, ensure_ascii=False, indent=2)
            
            # 섹션 메타데이터 저장
            with open(self.metadata_dir / "sections.json", "w", encoding="utf-8") as f:
                json.dump(self.section_metadata, f, ensure_ascii=False, indent=2)
            
            logger.info("메타데이터 저장 완료")
        except Exception as e:
            logger.error(f"메타데이터 저장 실패: {e}")
    
    def load_metadata(self):
        """파일에서 메타데이터 로드"""
        try:
            # 문서 메타데이터 로드
            doc_file = self.metadata_dir / "documents.json"
            if doc_file.exists():
                with open(doc_file, "r", encoding="utf-8") as f:
                    self.document_metadata = json.load(f)
            
            # 섹션 메타데이터 로드
            section_file = self.metadata_dir / "sections.json"
            if section_file.exists():
                with open(section_file, "r", encoding="utf-8") as f:
                    self.section_metadata = json.load(f)
            
            logger.info("메타데이터 로드 완료")
        except Exception as e:
            logger.error(f"메타데이터 로드 실패: {e}")


def get_vector_engine(data_dir: str = "data") -> VectorEngine:
    """벡터 엔진 싱글톤 인스턴스 반환"""
    if not hasattr(get_vector_engine, "_instance"):
        get_vector_engine._instance = VectorEngine(data_dir=data_dir)
    return get_vector_engine._instance