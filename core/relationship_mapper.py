"""
Relationship Mapper
전력시장 문서 간 연관성 매핑 시스템
"""

import logging
import re
import json
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import numpy as np
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    """관계 유형"""
    EXPLICIT_REFERENCE = "explicit_reference"  # 명시적 참조 (제1조, 별표1 등)
    SEMANTIC_SIMILARITY = "semantic_similarity"  # 의미적 유사성
    DOMAIN_RELATIONSHIP = "domain_relationship"  # 도메인 특화 관계
    HIERARCHICAL = "hierarchical"  # 계층 관계
    TEMPORAL = "temporal"  # 시간적 관계 (개정, 대체 등)
    CAUSAL = "causal"  # 인과 관계
    PROCEDURAL = "procedural"  # 절차적 관계


class RelationshipStrength(Enum):
    """관계 강도"""
    VERY_STRONG = "very_strong"  # 0.8-1.0
    STRONG = "strong"  # 0.6-0.8
    MODERATE = "moderate"  # 0.4-0.6
    WEAK = "weak"  # 0.2-0.4
    VERY_WEAK = "very_weak"  # 0.0-0.2


@dataclass
class DocumentRelationship:
    """문서 간 관계"""
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    strength: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    description: str
    evidence: List[str]  # 관계의 근거가 되는 텍스트들
    metadata: Dict[str, Any]
    created_at: str
    
    def get_strength_category(self) -> RelationshipStrength:
        """강도 카테고리 반환"""
        if self.strength >= 0.8:
            return RelationshipStrength.VERY_STRONG
        elif self.strength >= 0.6:
            return RelationshipStrength.STRONG
        elif self.strength >= 0.4:
            return RelationshipStrength.MODERATE
        elif self.strength >= 0.2:
            return RelationshipStrength.WEAK
        else:
            return RelationshipStrength.VERY_WEAK
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        result["relationship_type"] = self.relationship_type.value
        result["strength_category"] = self.get_strength_category().value
        return result


class PowerMarketRelationshipMapper:
    """
    전력시장 문서 연관성 매핑 시스템
    - 다양한 유형의 문서 간 관계 발견
    - AI가 활용하기 쉬운 그래프 구조 생성
    - 전력시장 도메인 특화 연관 규칙 적용
    """
    
    def __init__(self, embedder=None):
        self.embedder = embedder
        self.relationships: List[DocumentRelationship] = []
        
        # 전력시장 특화 관계 규칙
        self.domain_rules = self._initialize_domain_rules()
        self.reference_patterns = self._initialize_reference_patterns()
        self.semantic_thresholds = self._initialize_semantic_thresholds()
        
        # 관계 통계
        self.stats = {
            "total_relationships": 0,
            "by_type": defaultdict(int),
            "by_strength": defaultdict(int),
            "documents_analyzed": 0
        }
    
    def _initialize_domain_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """전력시장 도메인 특화 관계 규칙 초기화"""
        return {
            "발전계획": [
                {
                    "target_domains": ["계통운영", "예비력"],
                    "relationship": "operational_dependency",
                    "strength": 0.8,
                    "description": "발전계획은 계통운영과 예비력 확보에 직접적으로 연관"
                }
            ],
            "전력거래": [
                {
                    "target_domains": ["시장운영", "가격결정"],
                    "relationship": "market_mechanism",
                    "strength": 0.9,
                    "description": "전력거래는 시장운영과 가격결정의 핵심 메커니즘"
                }
            ],
            "계통운영": [
                {
                    "target_domains": ["송전제약", "안정성"],
                    "relationship": "technical_constraint",
                    "strength": 0.85,
                    "description": "계통운영은 송전제약과 안정성에 기술적으로 의존"
                }
            ],
            "예비력": [
                {
                    "target_domains": ["주파수조정", "보조서비스"],
                    "relationship": "service_provision",
                    "strength": 0.7,
                    "description": "예비력은 주파수조정과 보조서비스 제공의 수단"
                }
            ]
        }
    
    def _initialize_reference_patterns(self) -> List[Dict[str, Any]]:
        """참조 패턴 초기화"""
        return [
            {
                "pattern": r"제\s*(\d+)\s*조",
                "type": "article_reference",
                "strength": 0.9,
                "description": "조항 참조"
            },
            {
                "pattern": r"별표\s*(\d+)",
                "type": "annex_reference", 
                "strength": 0.8,
                "description": "별표 참조"
            },
            {
                "pattern": r"부록\s*([A-Z]|\d+)",
                "type": "appendix_reference",
                "strength": 0.8,
                "description": "부록 참조"
            },
            {
                "pattern": r"(\w+)\s*규칙",
                "type": "regulation_reference",
                "strength": 0.7,
                "description": "규칙 참조"
            },
            {
                "pattern": r"(\w+)\s*고시",
                "type": "notice_reference",
                "strength": 0.6,
                "description": "고시 참조"
            },
            {
                "pattern": r"(\d+)\.(\d+)\.(\d+)",
                "type": "section_reference",
                "strength": 0.7,
                "description": "절/항 참조"
            }
        ]
    
    def _initialize_semantic_thresholds(self) -> Dict[str, float]:
        """의미적 유사성 임계값 초기화"""
        return {
            "very_strong": 0.85,
            "strong": 0.70,
            "moderate": 0.55,
            "weak": 0.40,
            "minimum": 0.30
        }
    
    def analyze_document_relationships(self, documents: List[Dict[str, Any]]) -> List[DocumentRelationship]:
        """
        문서들 간의 관계 분석
        
        Args:
            documents: 처리된 문서들 (메타데이터와 임베딩 포함)
            
        Returns:
            발견된 관계들
        """
        logger.info(f"문서 간 관계 분석 시작: {len(documents)}개 문서")
        
        relationships = []
        
        # 1. 명시적 참조 관계 추출
        reference_rels = self._extract_explicit_references(documents)
        relationships.extend(reference_rels)
        
        # 2. 의미적 유사성 관계 추출
        if self.embedder:
            semantic_rels = self._extract_semantic_relationships(documents)
            relationships.extend(semantic_rels)
        
        # 3. 도메인 특화 관계 추출
        domain_rels = self._extract_domain_relationships(documents)
        relationships.extend(domain_rels)
        
        # 4. 계층적 관계 추출
        hierarchical_rels = self._extract_hierarchical_relationships(documents)
        relationships.extend(hierarchical_rels)
        
        # 5. 절차적 관계 추출
        procedural_rels = self._extract_procedural_relationships(documents)
        relationships.extend(procedural_rels)
        
        # 6. 중복 제거 및 관계 강화
        relationships = self._deduplicate_and_strengthen_relationships(relationships)
        
        # 통계 업데이트
        self._update_statistics(relationships, len(documents))
        
        logger.info(f"관계 분석 완료: {len(relationships)}개 관계 발견")
        return relationships
    
    def _extract_explicit_references(self, documents: List[Dict[str, Any]]) -> List[DocumentRelationship]:
        """명시적 참조 관계 추출"""
        relationships = []
        
        # 문서 ID별 인덱스 생성
        doc_by_id = {doc.get("document_id"): doc for doc in documents}
        
        for source_doc in documents:
            source_id = source_doc.get("document_id")
            source_text = source_doc.get("text", "")
            
            # 각 참조 패턴에 대해 매칭
            for pattern_info in self.reference_patterns:
                pattern = pattern_info["pattern"]
                matches = re.finditer(pattern, source_text, re.IGNORECASE)
                
                for match in matches:
                    reference = match.group()
                    
                    # 참조된 문서 찾기
                    target_docs = self._find_referenced_documents(reference, documents)
                    
                    for target_doc in target_docs:
                        target_id = target_doc.get("document_id")
                        
                        if source_id != target_id:  # 자기 참조 제외
                            relationship = DocumentRelationship(
                                source_id=source_id,
                                target_id=target_id,
                                relationship_type=RelationshipType.EXPLICIT_REFERENCE,
                                strength=pattern_info["strength"],
                                confidence=0.95,
                                description=f"{pattern_info['description']}: {reference}",
                                evidence=[match.group()],
                                metadata={
                                    "reference_text": reference,
                                    "pattern_type": pattern_info["type"],
                                    "context": source_text[max(0, match.start()-50):match.end()+50]
                                },
                                created_at=datetime.now().isoformat()
                            )
                            relationships.append(relationship)
        
        return relationships
    
    def _find_referenced_documents(self, reference: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """참조 텍스트와 매칭되는 문서들 찾기"""
        referenced_docs = []
        
        for doc in documents:
            # 문서 제목, 계층 정보에서 매칭 확인
            doc_title = doc.get("hierarchy_title", "")
            doc_number = doc.get("hierarchy_number", "")
            doc_path = doc.get("full_path", "")
            
            # 직접 매칭
            if (reference in doc_title or 
                reference in doc_number or 
                reference in doc_path):
                referenced_docs.append(doc)
            
            # 패턴 매칭 (예: "제1조"와 "제 1 조" 매칭)
            normalized_ref = re.sub(r'\s+', '', reference)
            normalized_title = re.sub(r'\s+', '', doc_title)
            normalized_number = re.sub(r'\s+', '', doc_number)
            
            if (normalized_ref in normalized_title or 
                normalized_ref in normalized_number):
                referenced_docs.append(doc)
        
        return referenced_docs
    
    def _extract_semantic_relationships(self, documents: List[Dict[str, Any]]) -> List[DocumentRelationship]:
        """의미적 유사성 기반 관계 추출"""
        relationships = []
        
        if not self.embedder:
            return relationships
        
        # 문서별 임베딩 추출
        embeddings = []
        for doc in documents:
            embedding = doc.get("embedding")
            if embedding is not None:
                if isinstance(embedding, list):
                    embedding = np.array(embedding)
                embeddings.append(embedding)
            else:
                # 임베딩이 없으면 텍스트로부터 생성
                text = doc.get("text", "")
                embedding = self.embedder.encode_text(text)
                embeddings.append(embedding)
        
        # 모든 문서 쌍에 대해 유사도 계산
        for i, source_doc in enumerate(documents):
            for j, target_doc in enumerate(documents[i+1:], i+1):
                if i >= len(embeddings) or j >= len(embeddings):
                    continue
                
                # 코사인 유사도 계산
                similarity = self._calculate_cosine_similarity(embeddings[i], embeddings[j])
                
                if similarity >= self.semantic_thresholds["minimum"]:
                    # 유사성 강도 결정
                    strength_category = self._categorize_similarity(similarity)
                    
                    relationship = DocumentRelationship(
                        source_id=source_doc.get("document_id"),
                        target_id=target_doc.get("document_id"),
                        relationship_type=RelationshipType.SEMANTIC_SIMILARITY,
                        strength=similarity,
                        confidence=0.85,
                        description=f"의미적 유사성 ({strength_category})",
                        evidence=[
                            source_doc.get("text", "")[:100] + "...",
                            target_doc.get("text", "")[:100] + "..."
                        ],
                        metadata={
                            "similarity_score": similarity,
                            "strength_category": strength_category
                        },
                        created_at=datetime.now().isoformat()
                    )
                    relationships.append(relationship)
        
        return relationships
    
    def _calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """코사인 유사도 계산"""
        try:
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.warning(f"유사도 계산 실패: {e}")
            return 0.0
    
    def _categorize_similarity(self, similarity: float) -> str:
        """유사도를 카테고리로 분류"""
        if similarity >= self.semantic_thresholds["very_strong"]:
            return "very_strong"
        elif similarity >= self.semantic_thresholds["strong"]:
            return "strong"
        elif similarity >= self.semantic_thresholds["moderate"]:
            return "moderate"
        elif similarity >= self.semantic_thresholds["weak"]:
            return "weak"
        else:
            return "very_weak"
    
    def _extract_domain_relationships(self, documents: List[Dict[str, Any]]) -> List[DocumentRelationship]:
        """도메인 특화 관계 추출"""
        relationships = []
        
        # 문서별 도메인 분류
        docs_by_domain = defaultdict(list)
        for doc in documents:
            domain = doc.get("market_domain", "기타")
            docs_by_domain[domain].append(doc)
        
        # 도메인 간 관계 규칙 적용
        for source_domain, rules in self.domain_rules.items():
            source_docs = docs_by_domain.get(source_domain, [])
            
            for rule in rules:
                target_domains = rule["target_domains"]
                
                for target_domain in target_domains:
                    target_docs = docs_by_domain.get(target_domain, [])
                    
                    # 해당 도메인 문서들 간 관계 생성
                    for source_doc in source_docs:
                        for target_doc in target_docs:
                            relationship = DocumentRelationship(
                                source_id=source_doc.get("document_id"),
                                target_id=target_doc.get("document_id"),
                                relationship_type=RelationshipType.DOMAIN_RELATIONSHIP,
                                strength=rule["strength"],
                                confidence=0.8,
                                description=rule["description"],
                                evidence=[
                                    f"Source domain: {source_domain}",
                                    f"Target domain: {target_domain}"
                                ],
                                metadata={
                                    "source_domain": source_domain,
                                    "target_domain": target_domain,
                                    "rule_type": rule["relationship"]
                                },
                                created_at=datetime.now().isoformat()
                            )
                            relationships.append(relationship)
        
        return relationships
    
    def _extract_hierarchical_relationships(self, documents: List[Dict[str, Any]]) -> List[DocumentRelationship]:
        """계층적 관계 추출"""
        relationships = []
        
        # 계층 정보를 가진 문서들 그룹화
        hierarchy_docs = [doc for doc in documents if doc.get("full_path")]
        
        for source_doc in hierarchy_docs:
            source_path = source_doc.get("full_path", "")
            source_level = source_path.count(">")
            
            for target_doc in hierarchy_docs:
                target_path = target_doc.get("full_path", "")
                target_level = target_path.count(">")
                
                # 부모-자식 관계 확인
                if (target_path.startswith(source_path + " >") and 
                    target_level == source_level + 1):
                    
                    relationship = DocumentRelationship(
                        source_id=source_doc.get("document_id"),
                        target_id=target_doc.get("document_id"),
                        relationship_type=RelationshipType.HIERARCHICAL,
                        strength=0.9,
                        confidence=0.95,
                        description="계층적 부모-자식 관계",
                        evidence=[source_path, target_path],
                        metadata={
                            "relationship_detail": "parent_child",
                            "source_level": source_level,
                            "target_level": target_level
                        },
                        created_at=datetime.now().isoformat()
                    )
                    relationships.append(relationship)
                
                # 형제 관계 확인
                elif (source_level == target_level and source_level > 0):
                    source_parent = " > ".join(source_path.split(" > ")[:-1])
                    target_parent = " > ".join(target_path.split(" > ")[:-1])
                    
                    if source_parent == target_parent and source_doc != target_doc:
                        relationship = DocumentRelationship(
                            source_id=source_doc.get("document_id"),
                            target_id=target_doc.get("document_id"),
                            relationship_type=RelationshipType.HIERARCHICAL,
                            strength=0.6,
                            confidence=0.9,
                            description="계층적 형제 관계",
                            evidence=[source_path, target_path],
                            metadata={
                                "relationship_detail": "sibling",
                                "common_parent": source_parent
                            },
                            created_at=datetime.now().isoformat()
                        )
                        relationships.append(relationship)
        
        return relationships
    
    def _extract_procedural_relationships(self, documents: List[Dict[str, Any]]) -> List[DocumentRelationship]:
        """절차적 관계 추출"""
        relationships = []
        
        # 절차 관련 키워드
        procedure_keywords = [
            "단계", "절차", "과정", "순서", "다음", "이후", "먼저", "그 다음",
            "1단계", "2단계", "1차", "2차", "먼저", "다음으로", "마지막으로"
        ]
        
        # 시간적 순서 키워드
        temporal_keywords = [
            "이전", "이후", "전에", "후에", "동안", "때", "시점",
            "개정", "변경", "폐지", "신설", "시행"
        ]
        
        for source_doc in documents:
            source_text = source_doc.get("text", "")
            
            # 절차적 키워드 확인
            has_procedure = any(keyword in source_text for keyword in procedure_keywords)
            has_temporal = any(keyword in source_text for keyword in temporal_keywords)
            
            if has_procedure or has_temporal:
                for target_doc in documents:
                    if source_doc == target_doc:
                        continue
                    
                    target_text = target_doc.get("text", "")
                    
                    # 공통 절차 키워드 확인
                    common_proc_keywords = [kw for kw in procedure_keywords if kw in target_text]
                    common_temp_keywords = [kw for kw in temporal_keywords if kw in target_text]
                    
                    if common_proc_keywords or common_temp_keywords:
                        strength = min(0.8, (len(common_proc_keywords) + len(common_temp_keywords)) * 0.2)
                        
                        if strength > 0.2:
                            rel_type = RelationshipType.PROCEDURAL if common_proc_keywords else RelationshipType.TEMPORAL
                            
                            relationship = DocumentRelationship(
                                source_id=source_doc.get("document_id"),
                                target_id=target_doc.get("document_id"),
                                relationship_type=rel_type,
                                strength=strength,
                                confidence=0.7,
                                description=f"절차적/시간적 연관성 (공통 키워드: {len(common_proc_keywords + common_temp_keywords)}개)",
                                evidence=common_proc_keywords + common_temp_keywords,
                                metadata={
                                    "common_procedure_keywords": common_proc_keywords,
                                    "common_temporal_keywords": common_temp_keywords
                                },
                                created_at=datetime.now().isoformat()
                            )
                            relationships.append(relationship)
        
        return relationships
    
    def _deduplicate_and_strengthen_relationships(self, relationships: List[DocumentRelationship]) -> List[DocumentRelationship]:
        """중복 관계 제거 및 관계 강화"""
        # 문서 쌍별로 관계들 그룹화
        pair_relationships = defaultdict(list)
        
        for rel in relationships:
            # 양방향 관계를 단방향으로 정규화
            source, target = sorted([rel.source_id, rel.target_id])
            pair_key = f"{source}_{target}"
            pair_relationships[pair_key].append(rel)
        
        # 각 문서 쌍에 대해 최적의 관계 선택/결합
        final_relationships = []
        
        for pair_key, pair_rels in pair_relationships.items():
            if len(pair_rels) == 1:
                final_relationships.append(pair_rels[0])
            else:
                # 여러 관계가 있는 경우 결합
                combined_rel = self._combine_relationships(pair_rels)
                final_relationships.append(combined_rel)
        
        return final_relationships
    
    def _combine_relationships(self, relationships: List[DocumentRelationship]) -> DocumentRelationship:
        """여러 관계를 하나로 결합"""
        if len(relationships) == 1:
            return relationships[0]
        
        # 가장 강한 관계를 기본으로 사용
        strongest_rel = max(relationships, key=lambda x: x.strength)
        
        # 모든 관계 유형 수집
        all_types = [rel.relationship_type for rel in relationships]
        all_evidence = []
        all_descriptions = []
        
        for rel in relationships:
            all_evidence.extend(rel.evidence)
            all_descriptions.append(rel.description)
        
        # 결합된 강도 계산 (최대값 + 보정)
        max_strength = max(rel.strength for rel in relationships)
        strength_boost = min(0.2, (len(relationships) - 1) * 0.05)
        combined_strength = min(1.0, max_strength + strength_boost)
        
        # 신뢰도 계산
        avg_confidence = sum(rel.confidence for rel in relationships) / len(relationships)
        
        return DocumentRelationship(
            source_id=strongest_rel.source_id,
            target_id=strongest_rel.target_id,
            relationship_type=strongest_rel.relationship_type,  # 가장 강한 관계의 타입 사용
            strength=combined_strength,
            confidence=avg_confidence,
            description=f"복합 관계: {'; '.join(set(all_descriptions))}",
            evidence=list(set(all_evidence)),
            metadata={
                "combined_from": [rel.relationship_type.value for rel in relationships],
                "original_count": len(relationships)
            },
            created_at=datetime.now().isoformat()
        )
    
    def _update_statistics(self, relationships: List[DocumentRelationship], doc_count: int):
        """통계 정보 업데이트"""
        self.stats["total_relationships"] = len(relationships)
        self.stats["documents_analyzed"] = doc_count
        
        # 유형별 통계
        for rel in relationships:
            self.stats["by_type"][rel.relationship_type.value] += 1
            self.stats["by_strength"][rel.get_strength_category().value] += 1
    
    def build_relationship_graph(self, relationships: List[DocumentRelationship]) -> Dict[str, Any]:
        """관계 그래프 구축"""
        
        # 노드와 엣지 추출
        nodes = set()
        edges = []
        
        for rel in relationships:
            nodes.add(rel.source_id)
            nodes.add(rel.target_id)
            
            edge = {
                "source": rel.source_id,
                "target": rel.target_id,
                "type": rel.relationship_type.value,
                "strength": rel.strength,
                "confidence": rel.confidence,
                "description": rel.description
            }
            edges.append(edge)
        
        # 노드별 통계 계산
        node_stats = {}
        for node in nodes:
            incoming = [e for e in edges if e["target"] == node]
            outgoing = [e for e in edges if e["source"] == node]
            
            node_stats[node] = {
                "incoming_count": len(incoming),
                "outgoing_count": len(outgoing),
                "total_connections": len(incoming) + len(outgoing),
                "avg_incoming_strength": np.mean([e["strength"] for e in incoming]) if incoming else 0,
                "avg_outgoing_strength": np.mean([e["strength"] for e in outgoing]) if outgoing else 0
            }
        
        return {
            "nodes": list(nodes),
            "edges": edges,
            "node_statistics": node_stats,
            "graph_statistics": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "density": len(edges) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0,
                "avg_degree": (2 * len(edges)) / len(nodes) if nodes else 0
            }
        }
    
    def get_related_documents(self, 
                            document_id: str, 
                            relationship_types: Optional[List[RelationshipType]] = None,
                            min_strength: float = 0.3,
                            max_results: int = 10) -> List[Dict[str, Any]]:
        """특정 문서와 관련된 문서들 조회"""
        
        related = []
        
        for rel in self.relationships:
            # 관계 유형 필터
            if relationship_types and rel.relationship_type not in relationship_types:
                continue
            
            # 강도 필터
            if rel.strength < min_strength:
                continue
            
            # 관련 문서 ID 추출
            if rel.source_id == document_id:
                related_id = rel.target_id
            elif rel.target_id == document_id:
                related_id = rel.source_id
            else:
                continue
            
            related.append({
                "document_id": related_id,
                "relationship": rel.to_dict(),
                "relevance_score": rel.strength * rel.confidence
            })
        
        # 관련성 점수로 정렬
        related.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return related[:max_results]
    
    def export_relationships(self, format: str = "json") -> str:
        """관계 데이터 내보내기"""
        data = {
            "relationships": [rel.to_dict() for rel in self.relationships],
            "statistics": dict(self.stats),
            "exported_at": datetime.now().isoformat()
        }
        
        if format.lower() == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"지원하지 않는 형식: {format}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """관계 매핑 통계 반환"""
        return {
            **dict(self.stats),
            "semantic_thresholds": self.semantic_thresholds,
            "domain_rules_count": len(self.domain_rules),
            "reference_patterns_count": len(self.reference_patterns)
        }


def get_relationship_mapper(embedder=None) -> PowerMarketRelationshipMapper:
    """Relationship Mapper 싱글톤 인스턴스 반환"""
    if not hasattr(get_relationship_mapper, "_instance"):
        get_relationship_mapper._instance = PowerMarketRelationshipMapper(embedder)
    return get_relationship_mapper._instance