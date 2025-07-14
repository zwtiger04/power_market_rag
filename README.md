# Power Market RAG System

전력시장 규칙 및 정산 공식을 위한 고도화된 RAG(Retrieval-Augmented Generation) 시스템

## 개요

이 프로젝트는 복잡한 전력시장 운영규칙과 정산 공식을 AI가 효율적으로 활용할 수 있도록 설계된 RAG 시스템입니다. 특히 제주 시범사업의 급전가능재생에너지자원 및 급전가능집합전력자원 정산에 특화되어 있습니다.

## 주요 기능

- **문서 처리**: PDF 형식의 전력시장 규칙 자동 처리 및 청킹
- **벡터 검색**: ChromaDB 기반 의미적 유사도 검색
- **하이브리드 검색**: 의미 검색 + 키워드 검색 결합
- **정산 공식 추출**: 별표 33의 실제 정산 공식 구조화
- **15분 단위 정산**: 실시간 전력시장의 15분 구간별 정산 지원
- **MCP 연동**: Claude Desktop 등 AI 도구와의 통합 (예정)

## 설치

```bash
# 저장소 클론
git clone https://github.com/yourusername/power_market_rag.git
cd power_market_rag

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 사용법

### 기본 사용

```python
from power_market_rag import PowerMarketRAG

# RAG 시스템 초기화
rag_system = PowerMarketRAG()
rag_system.initialize()

# 문서 로드
rag_system.load_documents("documents")

# 질문하기
result = rag_system.ask("급전가능재생에너지자원의 에너지정산금 계산 방법은?")
print(result['answer'])
```

### 정산 공식 조회

```python
from core.actual_formula_extractor import ActualFormulaExtractor

# 공식 추출기 초기화
extractor = ActualFormulaExtractor()

# 특정 공식 조회
formula = extractor.get_formula("renewable_energy_settlement")
print(formula.formula_text)
```

## 프로젝트 구조

```
power_market_rag/
├── core/                        # 핵심 모듈
│   └── actual_formula_extractor.py  # 정산 공식 추출
├── embeddings/                  # 임베딩 관련
│   ├── document_processor.py    # 문서 처리
│   └── text_embedder.py        # 텍스트 임베딩
├── vector_db/                   # 벡터 데이터베이스
│   └── vector_store.py         # ChromaDB 인터페이스
├── retrieval/                   # 검색 엔진
│   └── document_retriever.py   # 문서 검색
├── generation/                  # 답변 생성
│   └── answer_generator.py     # 컨텍스트 기반 생성
├── config/                      # 설정 파일
│   └── config.yaml            # 시스템 설정
├── documents/                   # PDF 문서 저장소
├── power_market_rag.py         # 메인 시스템
└── requirements.txt            # 의존성 목록
```

## 주요 정산 공식

### 1. 에너지정산금
```
MEPi,t = DA_MEP i,t + ∑q RT_MEP i,t,q
```

### 2. 15분 구간 변환계수
```
TPR_E i,t,q = MGO i,t,q / MGO i,t (∑TPR_E = 1.0)
```

### 3. 용량정산금
```
TPCP i,t = Min(A i,t, RAi,t, EAi) × RCP i × 1,000
```

## 설정

`config/config.yaml` 파일에서 주요 설정을 변경할 수 있습니다:

```yaml
EMBEDDING_MODEL: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
CHUNK_SIZE: 1000
CHUNK_OVERLAP: 200
TOP_K: 5
SIMILARITY_THRESHOLD: 0.7
```

## MCP 서버 (예정)

Claude Desktop과의 통합을 위한 MCP 서버 구현 예정:

```bash
# MCP 서버 실행
python mcp_server.py
```

## 기여

기여를 환영합니다! Pull Request를 보내주세요.

## 라이센스

MIT License

## 문의

프로젝트 관련 문의사항은 Issues를 통해 남겨주세요.
