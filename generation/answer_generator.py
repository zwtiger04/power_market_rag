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
    
    def calculate_confidence(self, context: str, query: str, answer: str) -> float:
        """답변의 신뢰도 계산"""
        try:
            confidence = 0.5  # 기본 신뢰도
            
            # 컨텍스트 품질 평가
            if len(context) > 500:
                confidence += 0.1
            
            # 질문과 컨텍스트의 관련성 평가
            query_words = set(query.lower().split())
            context_words = set(context.lower().split())
            
            overlap = len(query_words.intersection(context_words))
            if overlap > 0:
                confidence += min(0.3, overlap * 0.05)
            
            # 답변의 구체성 평가
            if any(keyword in answer for keyword in ["조", "항", "규정", "절차"]):
                confidence += 0.1
            
            # 소스 문서 수 고려
            source_count = context.count("[문서")
            confidence += min(0.1, source_count * 0.02)
            
            return min(1.0, confidence)
            
        except Exception as e:
            self.logger.error(f"신뢰도 계산 실패: {e}")
            return 0.5
    
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

if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    generator = PowerMarketAnswerGenerator()
    
    # 테스트용 컨텍스트와 질문
    test_context = """
    전력시장운영규칙 제16.4.1조에 의거하여 하루전발전계획을 수립합니다.
    발전계획 수립 절차는 다음과 같습니다:
    1. 11시: 초기입찰 입력
    2. 16시: 제주수요예측 연계
    3. 17시: 하루전발전계획 수립
    이러한 절차를 통해 전력 공급의 안정성을 확보합니다.
    """
    
    test_query = "하루전발전계획은 어떻게 수립되나요?"
    test_sources = ["전력시장운영규칙.pdf"]
    
    result = generator.generate_answer(test_context, test_query, test_sources)
    
    print("=== 답변 생성 결과 ===")
    print(f"답변: {result.answer}")
    print(f"신뢰도: {result.confidence:.3f}")
    print(f"추론: {result.reasoning}")
    print(f"메타데이터: {result.metadata}")
