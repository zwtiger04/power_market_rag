# Power Market RAG System - 프로젝트 컨텍스트

## 프로젝트 개요
전력시장 규칙과 정산 공식을 AI가 효율적으로 활용할 수 있는 고도화된 RAG(Retrieval-Augmented Generation) 시스템

### 주요 목표
- 복잡한 전력시장 규칙을 맥락에 따라 정확하게 제공
- 정산 수식의 변수 정의와 수식간 관계를 정교하게 구조화
- Claude Desktop 등 AI 도구와의 MCP 연동
- 실시간 문서 업데이트 및 증분 인덱싱

## 현재 구현 상태

### 1. 기본 RAG 시스템 ✅
- **DocumentProcessor**: PDF 문서 처리 및 청킹
- **PowerMarketEmbedder**: 다국어 임베딩 모델 (384차원)
- **VectorDatabase**: ChromaDB 기반 벡터 저장소
- **PowerMarketRetriever**: 하이브리드 검색 (의미 + 키워드)
- **PowerMarketAnswerGenerator**: 컨텍스트 기반 답변 생성

### 2. 정산 공식 추출 ✅
- **ActualFormulaExtractor**: 별표 33 실제 공식 추출기
- 8개 주요 정산 공식 구조화
  - 급전가능재생에너지자원 에너지정산금
  - 급전가능재생에너지자원 용량정산금
  - 급전가능집합전력자원 에너지정산금
  - 변동비보전정산금
  - 기대이익정산금
  - 가격 계산 공식들

### 3. 제주 시범사업 특화 ✅
- 15분 구간별 실시간 정산 (t=거래시간, q=15분구간)
- TPR_E (거래단위변환계수) 정확한 계산
- 급전가능재생에너지자원 중심 설계

## 다음 단계: MCP 서버 통합

### 1. MCP 서버 구현
```python
# mcp_server.py 구현 예정
- 문서 검색 도구
- 질문 답변 도구
- 정산 공식 조회 도구
- 벡터 DB 업데이트 도구
```

### 2. 실시간 업데이트 시스템
- 증분 업데이트 (IncrementalUpdater)
- 파일 감시 시스템 (DocumentWatcher)
- 메타데이터 기반 변경 추적

### 3. API 서버 (선택사항)
- FastAPI 기반 REST API
- 인증 및 권한 관리
- 비동기 처리

## 주요 파일 구조
```
power_market_rag/
├── power_market_rag.py          # 메인 RAG 시스템
├── core/
│   └── actual_formula_extractor.py  # 정산 공식 추출기
├── embeddings/
│   ├── document_processor.py    # 문서 처리
│   └── text_embedder.py        # 임베딩 생성
├── vector_db/
│   └── vector_store.py         # ChromaDB 관리
├── retrieval/
│   └── document_retriever.py   # 검색 엔진
├── generation/
│   └── answer_generator.py     # 답변 생성
├── config/
│   └── config.yaml            # 설정 파일
└── documents/                  # PDF 문서들
```

## 정산 공식 JSON 파일
- `jeju_settlement_formulas_updated.json`: 15분 정산 반영 버전
- `jeju_settlement_formulas_complete.json`: 전체 공식 모음
- `jeju_renewable_settlement_formulas.json`: 재생에너지 특화

## 기술 스택
- Python 3.8+
- ChromaDB (벡터 데이터베이스)
- Sentence-Transformers (임베딩)
- PyPDF2 (PDF 처리)
- FastAPI (API 서버 - 예정)
- MCP SDK (Claude Desktop 연동 - 예정)

## 설정 및 환경변수
```yaml
VECTOR_DB_TYPE: chromadb
VECTOR_DB_PATH: ./vector_db
COLLECTION_NAME: power_market_docs
EMBEDDING_MODEL: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
CHUNK_SIZE: 1000
CHUNK_OVERLAP: 200
TOP_K: 5
SIMILARITY_THRESHOLD: 0.7
```

## 테스트 가능한 질문들
1. "급전가능재생에너지자원의 에너지정산금 계산 방법은?"
2. "15분 단위 실시간 정산에서 TPR_E는 어떻게 계산하나요?"
3. "제주 시범사업의 용량정산금 공식을 알려주세요"
4. "급전가능집합전력자원의 기대이익정산금은?"

## 향후 개선 사항
1. 임베딩 모델 768차원으로 업그레이드
2. 별표 2 일반 정산 규칙 추가
3. 메타데이터 강화 (장/절/조 구조)
4. 수식 시각화 기능
5. 실시간 규칙 변경 알림

## 프로젝트 재개 시 체크리스트
- [ ] 가상환경 활성화
- [ ] ChromaDB 서버 실행 확인
- [ ] 문서 폴더 경로 확인
- [ ] MCP 서버 구현 시작
- [ ] GitHub 리포지토리 설정

---
마지막 업데이트: 2025-07-14