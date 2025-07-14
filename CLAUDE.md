# CLAUDE.md - AI 어시스턴트 작업 가이드

## 🎯 프로젝트 개요
Power Market RAG System - 전력시장 규칙 및 정산 공식을 위한 고도화된 RAG 시스템

**GitHub Repository**: https://github.com/zwtiger04/power_market_rag

## 📋 작업 시작 전 필수 체크리스트

### 1. 맥락 분석 읽기 📖
작업을 시작하기 전에 **반드시** 다음 문서들을 읽고 현재 상황을 파악하세요:

```bash
# 1순위: 프로젝트 전체 맥락
cat PROJECT_CONTEXT.md

# 2순위: 사용자 가이드 (변경사항 확인)
cat README.md

# 3순위: 최근 커밋 메시지 확인
git log --oneline -5
```

**중요**: 메모리에서 최근 작업 내용도 확인하세요
```python
# 메모리 도구 사용하여 프로젝트 관련 최근 정보 조회
mcp__memory__recall_memory("power_market_rag 최근 작업")
```

### 2. 현재 상태 확인 🔍
```bash
# Git 상태 확인
git status

# 브랜치 확인
git branch -v

# 원격 저장소 상태 확인
git remote -v
```

## 🔄 작업 완료 후 필수 프로세스

### 1. 맥락 문서 업데이트 📝

#### PROJECT_CONTEXT.md 업데이트
- **언제**: 주요 기능 추가/변경, 아키텍처 변경, 새로운 모듈 추가
- **내용**: 현재 구현 상태, 다음 단계, 주요 파일 경로, 설정 변경사항

```bash
# 예시 업데이트 섹션
## 현재 구현 상태
- [x] 기본 RAG 시스템
- [x] 정산 공식 추출
- [ ] MCP 서버 구현 ← 현재 작업 중

## 최근 변경사항 (날짜)
- MCP 서버 기본 구조 구현
- 실시간 업데이트 시스템 추가
```

#### README.md 업데이트
- **언제**: 사용법 변경, 새로운 기능 추가, 설치 방법 변경
- **내용**: 사용자가 알아야 할 변경사항, 새로운 예시 코드

### 2. 메모리 업데이트 🧠
작업 완료 후 반드시 메모리에 저장하세요:

```python
mcp__memory__store_memory(
    content="작업 완료 내용 요약: 무엇을 했는지, 어떤 파일이 변경되었는지, 다음에 할 일",
    metadata={
        "tags": "power_market_rag,작업타입,주요기능", 
        "type": "progress_update"
    }
)
```

**메모리 저장 가이드라인**:
- 구체적인 변경사항 기록
- 문제 해결 과정 기록
- 다음 작업자가 알아야 할 중요한 정보
- 실패한 시도와 그 이유도 기록

### 3. Git 커밋 - 백업 포인트 생성 💾

#### 커밋 타이밍
- **필수**: 주요 기능 구현 완료 후
- **권장**: 일일 작업 종료 시
- **선택**: 중간 마일스톤 달성 시

#### 커밋 메시지 템플릿
```bash
git add .
git commit -m "$(cat <<'EOF'
[작업타입]: 간단한 요약

상세 내용:
- 구현한 기능 1
- 수정한 내용 2
- 추가한 파일들

다음 단계:
- TODO 항목 1
- TODO 항목 2

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

#### 작업 타입 분류
- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 업데이트
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 기타 작업 (설정, 빌드 등)

#### 커밋 후 푸시
```bash
git push origin main
```

## 🚨 중요한 작업 패턴

### 작업 시작 시
1. **맥락 읽기** → PROJECT_CONTEXT.md + 메모리 조회
2. **현재 상태 파악** → git status, 파일 구조 확인
3. **작업 계획** → TodoWrite 도구로 계획 수립

### 작업 진행 중
1. **점진적 커밋** → 의미있는 단위로 자주 커밋
2. **문서화** → 복잡한 로직은 즉시 주석 추가
3. **테스트** → 가능한 경우 간단한 테스트 실행

### 작업 완료 시
1. **문서 업데이트** → PROJECT_CONTEXT.md, README.md
2. **메모리 저장** → 작업 내용과 다음 단계
3. **최종 커밋** → 완성된 기능의 백업 포인트
4. **푸시** → GitHub에 안전하게 저장

## 📂 주요 파일 및 디렉토리

### 핵심 문서
- `PROJECT_CONTEXT.md` - 프로젝트 전체 맥락 (작업자용)
- `README.md` - 사용자 가이드
- `CLAUDE.md` - 이 파일 (AI 어시스턴트용 가이드)

### 핵심 코드
- `power_market_rag.py` - 메인 RAG 시스템
- `core/actual_formula_extractor.py` - 정산 공식 추출기
- `config/config.yaml` - 시스템 설정

### 데이터
- `documents/` - PDF 문서들
- `jeju_settlement_formulas_*.json` - 정산 공식 데이터

## 🔧 자주 사용하는 명령어

### 프로젝트 상태 확인
```bash
# 전체 프로젝트 구조 확인
tree -I '__pycache__|*.pyc|vector_db|*.log' -L 3

# 최근 변경된 파일들
git diff --name-only HEAD~1

# 메인 시스템 테스트
python power_market_rag.py
```

### 개발 환경 설정
```bash
# 가상환경 활성화 (필요시)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

## 🎯 현재 프로젝트 상태

**마지막 업데이트**: 2025-07-14

**완료된 작업**:
- ✅ 기본 RAG 시스템 구현
- ✅ 별표 33 정산 공식 추출
- ✅ 15분 단위 실시간 정산 지원
- ✅ GitHub 리포지토리 설정

**진행 중인 작업**:
- 🔄 MCP 서버 구현

**다음 단계**:
- 📋 MCP 서버 구현 완료
- 📋 실시간 업데이트 시스템
- 📋 Claude Desktop 통합 테스트

## 💡 팁과 주의사항

### 작업 효율성
1. **작은 단위로 자주 커밋** - 되돌아갈 수 있는 지점을 많이 만드세요
2. **명확한 커밋 메시지** - 나중에 특정 시점을 찾기 쉽게
3. **문서 우선** - 코드보다 문서를 먼저 업데이트하면 방향성 유지

### 주의사항
1. **큰 파일 추가 금지** - PDF, 바이너리 파일은 .gitignore 확인
2. **민감정보 제외** - API 키, 비밀번호 등은 절대 커밋하지 않기
3. **브랜치 정책** - main 브랜치는 항상 작동하는 상태 유지

---

**이 가이드를 따라 체계적으로 작업하면 프로젝트의 연속성과 품질을 보장할 수 있습니다.**