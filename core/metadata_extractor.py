"""
메타데이터 추출기
AI가 최대한 활용할 수 있도록 전력시장 문서의 메타데이터를 풍부화
"""

import logging
import re
from typing import Dict, List, Optional, Union, Any, Tuple, Set
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """
    전력시장 문서 메타데이터 추출 및 풍부화
    
    기능:
    - 전력시장 도메인 특화 정보 추출
    - 문서 구조 및 유형 분석
    - 엔티티 및 키워드 추출
    - 관계 정보 매핑
    - AI 친화적 메타데이터 구조화
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.metadata_dir = self.data_dir / "metadata"
        self.rules_dir = self.data_dir / "extraction_rules"
        
        # 디렉토리 생성
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        
        # 전력시장 도메인 특화 패턴 및 규칙
        self._initialize_power_market_patterns()
        
        # 추출 통계
        self.extraction_stats = {
            "documents_processed": 0,
            "entities_extracted": 0,
            "keywords_extracted": 0,
            "relations_mapped": 0
        }
    
    def _initialize_power_market_patterns(self):
        """전력시장 도메인 특화 패턴 초기화"""
        
        # 전력시장 엔티티 패턴
        self.entity_patterns = {
            "market_types": [
                r"현물시장", r"선도시장", r"용량시장", r"보조서비스시장",
                r"실시간시장", r"당일시장", r"전일시장"
            ],
            "participants": [
                r"발전사업자", r"전력거래소", r"한전", r"한국전력공사",
                r"민자발전사", r"공기업발전사", r"재생에너지발전사"
            ],
            "regulations": [
                r"전력시장운영규칙", r"전력거래규칙", r"급전운영규칙",
                r"정산규칙", r"요금규칙", r"전기사업법"
            ],
            "technical_terms": [
                r"SMP", r"시스템한계가격", r"급전지시", r"예비력",
                r"주파수조정", r"전압조정", r"계통운영", r"송전제약"
            ],
            "units": [
                r"MW", r"MWh", r"GW", r"GWh", r"kW", r"kWh",
                r"원/MWh", r"₩/MWh", r"Hz", r"kV"
            ],
            "time_periods": [
                r"\d{4}년\s*\d{1,2}월", r"\d{4}-\d{2}-\d{2}",
                r"\d{2}:\d{2}", r"시간대", r"첨두시간", r"경부하시간"
            ]
        }
        
        # 문서 유형 패턴
        self.document_type_patterns = {
            "규칙": [r"규칙", r"규정", r"지침", r"기준"],
            "고시": [r"고시", r"공고", r"알림"],
            "절차": [r"절차", r"매뉴얼", r"가이드", r"안내"],
            "양식": [r"양식", r"서식", r"신청서", r"보고서"],
            "기술기준": [r"기술기준", r"기술규격", r"표준", r"규격"],
            "계약": [r"계약", r"협약", r"약정", r"합의"]
        }
        
        # 중요도 키워드
        self.importance_keywords = {
            "critical": ["필수", "의무", "반드시", "금지", "제재"],
            "important": ["중요", "주의", "권장", "권고", "고려"],
            "informational": ["참고", "안내", "예시", "부록", "별첨"]
        }
    
    def extract_metadata(self, processed_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        처리된 문서에서 풍부한 메타데이터 추출
        
        Args:
            processed_doc: MultimodalProcessor에서 처리된 문서 데이터
            
        Returns:
            AI 최적화된 메타데이터
        """
        logger.info(f"메타데이터 추출 시작: {processed_doc.get('document_id', 'unknown')}")
        
        start_time = datetime.now()
        
        try:
            # 기본 메타데이터 구조
            metadata = {
                "document_id": processed_doc["document_id"],
                "extraction_timestamp": datetime.now().isoformat(),
                "power_market_metadata": {},
                "structural_metadata": {},
                "content_metadata": {},
                "ai_enhancement": {},
                "relationships": [],
                "quality_indicators": {}
            }
            
            # 1. 전력시장 특화 메타데이터 추출
            metadata["power_market_metadata"] = self._extract_power_market_metadata(processed_doc)
            
            # 2. 구조적 메타데이터 추출
            metadata["structural_metadata"] = self._extract_structural_metadata(processed_doc)
            
            # 3. 콘텐츠 메타데이터 추출
            metadata["content_metadata"] = self._extract_content_metadata(processed_doc)
            
            # 4. AI 활용 최적화 정보
            metadata["ai_enhancement"] = self._generate_ai_enhancement_data(processed_doc)
            
            # 5. 관계 정보 매핑
            metadata["relationships"] = self._extract_relationships(processed_doc)
            
            # 6. 품질 지표 계산
            metadata["quality_indicators"] = self._calculate_quality_indicators(processed_doc, metadata)
            
            # 처리 시간 기록
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            metadata["processing_time_ms"] = processing_time
            
            # 통계 업데이트
            self._update_extraction_stats(metadata)
            
            logger.info(f"메타데이터 추출 완료: {processed_doc['document_id']} ({processing_time:.2f}ms)")
            return metadata
            
        except Exception as e:
            logger.error(f"메타데이터 추출 실패: {e}")
            return self._create_error_metadata(processed_doc, str(e))
    
    def _extract_power_market_metadata(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """전력시장 특화 메타데이터 추출"""
        content = doc.get("content", {}).get("document", "")
        
        power_metadata = {
            "market_entities": {},
            "regulations_referenced": [],
            "technical_specifications": [],
            "market_segments": [],
            "compliance_requirements": [],
            "document_classification": {}
        }
        
        # 엔티티 추출
        for entity_type, patterns in self.entity_patterns.items():
            entities = []
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        "text": match.group(),
                        "start_pos": match.start(),
                        "end_pos": match.end(),
                        "context": content[max(0, match.start()-30):match.end()+30]
                    })
            
            if entities:
                power_metadata["market_entities"][entity_type] = entities
        
        # 문서 분류
        doc_classification = self._classify_document_type(content)
        power_metadata["document_classification"] = doc_classification
        
        # 규제 요구사항 추출
        compliance_reqs = self._extract_compliance_requirements(content)
        power_metadata["compliance_requirements"] = compliance_reqs
        
        return power_metadata
    
    def _extract_structural_metadata(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """문서 구조 메타데이터 추출"""
        content = doc.get("content", {})
        multimodal = doc.get("multimodal_content", {})
        
        return {
            "document_structure": {
                "total_sections": len(content.get("sections", [])),
                "total_paragraphs": len(content.get("paragraphs", [])),
                "total_sentences": len(content.get("sentences", [])),
                "has_sections": len(content.get("sections", [])) > 0,
                "section_hierarchy": self._analyze_section_hierarchy(content.get("sections", []))
            },
            "multimodal_elements": {
                "total_images": len(multimodal.get("images", [])),
                "total_tables": len(multimodal.get("tables", [])),
                "total_formulas": len(multimodal.get("formulas", [])),
                "has_visual_content": len(multimodal.get("images", [])) > 0,
                "has_structured_data": len(multimodal.get("tables", [])) > 0,
                "has_mathematical_content": len(multimodal.get("formulas", [])) > 0
            },
            "content_distribution": self._analyze_content_distribution(content)
        }
    
    def _extract_content_metadata(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """콘텐츠 메타데이터 추출"""
        content = doc.get("content", {}).get("document", "")
        
        return {
            "language_analysis": {
                "primary_language": self._detect_language(content),
                "text_complexity": self._calculate_text_complexity(content),
                "readability_score": self._calculate_readability(content)
            },
            "keyword_analysis": {
                "top_keywords": self._extract_top_keywords(content),
                "domain_keywords": self._extract_domain_keywords(content),
                "technical_terms": self._extract_technical_terms(content)
            },
            "content_characteristics": {
                "document_length": len(content),
                "word_count": len(content.split()),
                "sentence_count": len(re.split(r'[.!?]+', content)),
                "average_sentence_length": self._calculate_avg_sentence_length(content),
                "has_numbered_lists": bool(re.search(r'\d+\.', content)),
                "has_bullet_points": bool(re.search(r'[•·▪▫]', content))
            }
        }
    
    def _generate_ai_enhancement_data(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """AI 활용 최적화 정보 생성"""
        content = doc.get("content", {})
        
        return {
            "searchability": {
                "key_search_terms": self._generate_search_terms(content),
                "semantic_concepts": self._extract_semantic_concepts(content),
                "question_answering_hints": self._generate_qa_hints(content)
            },
            "summarization_support": {
                "main_topics": self._identify_main_topics(content),
                "key_points": self._extract_key_points(content),
                "summary_candidates": self._identify_summary_candidates(content)
            },
            "context_enhancement": {
                "prerequisite_knowledge": self._identify_prerequisites(content),
                "related_concepts": self._identify_related_concepts(content),
                "cross_references": self._extract_cross_references(content)
            }
        }
    
    def _extract_relationships(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """관계 정보 추출"""
        content = doc.get("content", {}).get("document", "")
        relationships = []
        
        # 참조 관계 추출
        ref_patterns = [
            r"제\s*(\d+)\s*조",  # 조항 참조
            r"별표\s*(\d+)",     # 별표 참조
            r"부록\s*(\w+)",     # 부록 참조
            r"(\w+)\s*규칙",     # 규칙 참조
        ]
        
        for pattern in ref_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                relationships.append({
                    "type": "reference",
                    "source": doc["document_id"],
                    "target": match.group(),
                    "context": content[max(0, match.start()-50):match.end()+50],
                    "position": match.start()
                })
        
        return relationships
    
    def _calculate_quality_indicators(self, doc: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """품질 지표 계산"""
        content = doc.get("content", {})
        
        # 완성도 점수
        completeness_score = 0.0
        if content.get("document"): completeness_score += 0.3
        if content.get("sections"): completeness_score += 0.2
        if content.get("paragraphs"): completeness_score += 0.2
        if content.get("sentences"): completeness_score += 0.2
        if doc.get("multimodal_content"): completeness_score += 0.1
        
        # 구조화 점수
        structure_score = min(1.0, len(content.get("sections", [])) * 0.1)
        
        # 메타데이터 풍부도
        metadata_richness = len([v for v in metadata.values() if v]) / 10
        
        return {
            "completeness_score": round(completeness_score, 2),
            "structure_score": round(structure_score, 2),
            "metadata_richness": round(min(1.0, metadata_richness), 2),
            "overall_quality": round((completeness_score + structure_score + metadata_richness) / 3, 2),
            "processing_success": "error" not in doc
        }
    
    def _classify_document_type(self, content: str) -> Dict[str, Any]:
        """문서 유형 분류"""
        classification = {
            "primary_type": "unknown",
            "secondary_types": [],
            "confidence_scores": {}
        }
        
        max_score = 0
        for doc_type, patterns in self.document_type_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                score += matches
            
            classification["confidence_scores"][doc_type] = score
            
            if score > max_score:
                max_score = score
                classification["primary_type"] = doc_type
        
        # 부차 유형 추출 (점수가 0보다 큰 모든 유형)
        classification["secondary_types"] = [
            doc_type for doc_type, score in classification["confidence_scores"].items()
            if score > 0 and doc_type != classification["primary_type"]
        ]
        
        return classification
    
    def _extract_compliance_requirements(self, content: str) -> List[Dict[str, Any]]:
        """규제 요구사항 추출"""
        requirements = []
        
        # 의무사항 패턴
        obligation_patterns = [
            r"(반드시|필수적으로|의무적으로)\s+([^.!?]+)",
            r"([^.!?]+)\s+(하여야\s*한다|해야\s*한다)",
            r"(금지|제한|불가)\s+([^.!?]+)"
        ]
        
        for pattern in obligation_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                requirements.append({
                    "type": "obligation",
                    "text": match.group(),
                    "context": content[max(0, match.start()-50):match.end()+50],
                    "importance": self._assess_requirement_importance(match.group())
                })
        
        return requirements
    
    def _analyze_section_hierarchy(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """섹션 계층 구조 분석"""
        if not sections:
            return {"depth": 0, "structure": "flat"}
        
        hierarchy = {
            "depth": 1,
            "structure": "hierarchical",
            "section_types": [],
            "numbering_scheme": "unknown"
        }
        
        # 번호 체계 분석
        for section in sections:
            title = section.get("title", "")
            if re.match(r"제\s*\d+\s*조", title):
                hierarchy["numbering_scheme"] = "legal"
            elif re.match(r"\d+\.", title):
                hierarchy["numbering_scheme"] = "decimal"
        
        return hierarchy
    
    def _analyze_content_distribution(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """콘텐츠 분포 분석"""
        sections = content.get("sections", [])
        paragraphs = content.get("paragraphs", [])
        
        distribution = {
            "section_lengths": [len(s.get("content", "")) for s in sections],
            "paragraph_lengths": [len(p.get("content", "")) for p in paragraphs],
            "content_balance": "unknown"
        }
        
        if distribution["section_lengths"]:
            avg_section_length = sum(distribution["section_lengths"]) / len(distribution["section_lengths"])
            if max(distribution["section_lengths"]) > avg_section_length * 3:
                distribution["content_balance"] = "uneven"
            else:
                distribution["content_balance"] = "balanced"
        
        return distribution
    
    def _detect_language(self, content: str) -> str:
        """언어 감지 (간단한 방법)"""
        korean_chars = len(re.findall(r'[가-힣]', content))
        english_chars = len(re.findall(r'[a-zA-Z]', content))
        
        if korean_chars > english_chars:
            return "korean"
        elif english_chars > korean_chars:
            return "english"
        else:
            return "mixed"
    
    def _calculate_text_complexity(self, content: str) -> str:
        """텍스트 복잡도 계산"""
        sentences = re.split(r'[.!?]+', content)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        if avg_sentence_length > 25:
            return "complex"
        elif avg_sentence_length > 15:
            return "moderate"
        else:
            return "simple"
    
    def _calculate_readability(self, content: str) -> float:
        """가독성 점수 계산 (간단한 방법)"""
        sentences = re.split(r'[.!?]+', content)
        words = content.split()
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        complex_words = len([w for w in words if len(w) > 6])
        complex_ratio = complex_words / len(words)
        
        # 간단한 가독성 공식 (낮을수록 읽기 쉬움)
        readability = avg_sentence_length * 0.5 + complex_ratio * 100
        return round(max(0, min(100, readability)), 2)
    
    def _extract_top_keywords(self, content: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """상위 키워드 추출"""
        # 간단한 키워드 추출 (개선 가능)
        words = re.findall(r'[가-힣a-zA-Z]{2,}', content.lower())
        word_freq = {}
        
        for word in words:
            if len(word) > 2:  # 2글자 이상만
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 빈도순 정렬
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"keyword": word, "frequency": freq, "importance": min(1.0, freq / 10)}
            for word, freq in sorted_words[:top_k]
        ]
    
    def _extract_domain_keywords(self, content: str) -> List[str]:
        """도메인 특화 키워드 추출"""
        domain_keywords = []
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                domain_keywords.extend(matches)
        
        return list(set(domain_keywords))
    
    def _extract_technical_terms(self, content: str) -> List[Dict[str, Any]]:
        """기술 용어 추출"""
        technical_terms = []
        
        # 기술 용어 패턴
        patterns = [
            r'[A-Z]{2,}',  # 약어
            r'\d+[A-Za-z]+',  # 숫자+단위
            r'[가-힣]+\s*\([A-Za-z]+\)',  # 한글(영문)
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                technical_terms.append({
                    "term": match.group(),
                    "position": match.start(),
                    "context": content[max(0, match.start()-20):match.end()+20]
                })
        
        return technical_terms
    
    def _calculate_avg_sentence_length(self, content: str) -> float:
        """평균 문장 길이 계산"""
        sentences = re.split(r'[.!?]+', content)
        if not sentences:
            return 0.0
        
        total_words = sum(len(s.split()) for s in sentences)
        return round(total_words / len(sentences), 2)
    
    def _generate_search_terms(self, content: Dict[str, Any]) -> List[str]:
        """검색 용어 생성"""
        document_text = content.get("document", "")
        sections = content.get("sections", [])
        
        search_terms = []
        
        # 섹션 제목에서 검색어 추출
        for section in sections:
            title = section.get("title", "")
            if title:
                search_terms.extend(title.split())
        
        # 도메인 키워드 추가
        search_terms.extend(self._extract_domain_keywords(document_text))
        
        return list(set(search_terms))[:50]  # 상위 50개
    
    def _extract_semantic_concepts(self, content: Dict[str, Any]) -> List[str]:
        """의미적 개념 추출"""
        # 간단한 구현 - 향후 NLP 모델로 개선 가능
        concepts = []
        
        concept_patterns = [
            r"([가-힣]{2,})\s*(정의|의미|개념)",
            r"([가-힣]{2,})\s*(이란|라고\s*함)",
            r"([가-힣]{2,})\s*:\s*([^.]+)"
        ]
        
        document_text = content.get("document", "")
        for pattern in concept_patterns:
            matches = re.findall(pattern, document_text)
            concepts.extend([match[0] if isinstance(match, tuple) else match for match in matches])
        
        return list(set(concepts))[:20]
    
    def _generate_qa_hints(self, content: Dict[str, Any]) -> List[Dict[str, str]]:
        """Q&A 힌트 생성"""
        qa_hints = []
        
        # 정의문에서 Q&A 생성
        document_text = content.get("document", "")
        definition_patterns = [
            r"([가-힣a-zA-Z\s]+)\s*(이란|라고\s*함은)\s*([^.]+)",
            r"([가-힣a-zA-Z\s]+)\s*:\s*([^.]+)"
        ]
        
        for pattern in definition_patterns:
            matches = re.finditer(pattern, document_text)
            for match in matches:
                if len(match.groups()) >= 2:
                    term = match.group(1).strip()
                    definition = match.group(2).strip()
                    
                    qa_hints.append({
                        "question": f"{term}이란 무엇인가요?",
                        "answer_hint": definition,
                        "source_context": match.group()
                    })
        
        return qa_hints[:10]
    
    def _identify_main_topics(self, content: Dict[str, Any]) -> List[str]:
        """주요 주제 식별"""
        sections = content.get("sections", [])
        
        # 섹션 제목에서 주제 추출
        topics = []
        for section in sections:
            title = section.get("title", "")
            if title and len(title) > 3:
                # 조항 번호 등 제거
                clean_title = re.sub(r'^제\s*\d+\s*[조항호]\s*', '', title)
                clean_title = re.sub(r'^\d+\.\s*', '', clean_title)
                if clean_title:
                    topics.append(clean_title.strip())
        
        return topics[:10]
    
    def _extract_key_points(self, content: Dict[str, Any]) -> List[str]:
        """핵심 포인트 추출"""
        document_text = content.get("document", "")
        
        # 중요한 문장 패턴
        important_patterns = [
            r"(필수|중요|주의|반드시)[^.]+[.]",
            r"(금지|제한|불가)[^.]+[.]",
            r"(의무|책임)[^.]+[.]"
        ]
        
        key_points = []
        for pattern in important_patterns:
            matches = re.findall(pattern, document_text)
            key_points.extend(matches)
        
        return key_points[:15]
    
    def _identify_summary_candidates(self, content: Dict[str, Any]) -> List[str]:
        """요약 후보 식별"""
        paragraphs = content.get("paragraphs", [])
        
        # 첫 번째와 마지막 문단, 그리고 중간 정도의 긴 문단들
        candidates = []
        
        if paragraphs:
            # 첫 번째 문단
            if paragraphs[0].get("content"):
                candidates.append(paragraphs[0]["content"][:200])
            
            # 중간에 긴 문단들
            for para in paragraphs[1:-1]:
                content_text = para.get("content", "")
                if len(content_text) > 100:
                    candidates.append(content_text[:200])
            
            # 마지막 문단
            if len(paragraphs) > 1 and paragraphs[-1].get("content"):
                candidates.append(paragraphs[-1]["content"][:200])
        
        return candidates[:5]
    
    def _identify_prerequisites(self, content: Dict[str, Any]) -> List[str]:
        """전제 조건 식별"""
        document_text = content.get("document", "")
        
        prerequisite_patterns = [
            r"(전제|조건|요건|자격)[^.]+[.]",
            r"([^.]+)\s*(경우에\s*한하여|에\s*한정하여)",
            r"(우선|선행|사전)[^.]+[.]"
        ]
        
        prerequisites = []
        for pattern in prerequisite_patterns:
            matches = re.findall(pattern, document_text)
            prerequisites.extend(matches)
        
        return prerequisites[:10]
    
    def _identify_related_concepts(self, content: Dict[str, Any]) -> List[str]:
        """관련 개념 식별"""
        # 문서 내 공출현하는 용어들을 관련 개념으로 간주
        document_text = content.get("document", "")
        domain_keywords = self._extract_domain_keywords(document_text)
        
        # 간단한 구현: 자주 언급되는 도메인 키워드들
        return domain_keywords[:15]
    
    def _extract_cross_references(self, content: Dict[str, Any]) -> List[Dict[str, str]]:
        """상호 참조 추출"""
        document_text = content.get("document", "")
        
        ref_patterns = [
            (r"제\s*(\d+)\s*조", "article"),
            (r"별표\s*(\d+)", "annex"),
            (r"부록\s*(\w+)", "appendix"),
            (r"(\w+)\s*규칙", "regulation")
        ]
        
        references = []
        for pattern, ref_type in ref_patterns:
            matches = re.finditer(pattern, document_text)
            for match in matches:
                references.append({
                    "type": ref_type,
                    "reference": match.group(),
                    "context": document_text[max(0, match.start()-30):match.end()+30]
                })
        
        return references[:20]
    
    def _assess_requirement_importance(self, requirement_text: str) -> str:
        """요구사항 중요도 평가"""
        for importance, keywords in self.importance_keywords.items():
            for keyword in keywords:
                if keyword in requirement_text:
                    return importance
        return "informational"
    
    def _update_extraction_stats(self, metadata: Dict[str, Any]):
        """추출 통계 업데이트"""
        self.extraction_stats["documents_processed"] += 1
        
        # 엔티티 수 계산
        power_metadata = metadata.get("power_market_metadata", {})
        entities = power_metadata.get("market_entities", {})
        entity_count = sum(len(entity_list) for entity_list in entities.values())
        self.extraction_stats["entities_extracted"] += entity_count
        
        # 키워드 수 계산
        content_metadata = metadata.get("content_metadata", {})
        keyword_analysis = content_metadata.get("keyword_analysis", {})
        keyword_count = len(keyword_analysis.get("top_keywords", []))
        self.extraction_stats["keywords_extracted"] += keyword_count
        
        # 관계 수 계산
        relationships = metadata.get("relationships", [])
        self.extraction_stats["relations_mapped"] += len(relationships)
    
    def _create_error_metadata(self, doc: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """오류 메타데이터 생성"""
        return {
            "document_id": doc.get("document_id", "unknown"),
            "extraction_timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "power_market_metadata": {},
            "structural_metadata": {},
            "content_metadata": {},
            "ai_enhancement": {},
            "relationships": [],
            "quality_indicators": {"overall_quality": 0.0, "processing_success": False}
        }
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """추출 통계 반환"""
        return {
            **self.extraction_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_metadata(self, metadata: Dict[str, Any]) -> bool:
        """메타데이터를 파일로 저장"""
        try:
            doc_id = metadata["document_id"]
            output_file = self.metadata_dir / f"{doc_id}_metadata.json"
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"메타데이터 저장 완료: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"메타데이터 저장 실패: {e}")
            return False


def get_metadata_extractor(data_dir: str = "data") -> MetadataExtractor:
    """메타데이터 추출기 싱글톤 인스턴스 반환"""
    if not hasattr(get_metadata_extractor, "_instance"):
        get_metadata_extractor._instance = MetadataExtractor(data_dir=data_dir)
    return get_metadata_extractor._instance