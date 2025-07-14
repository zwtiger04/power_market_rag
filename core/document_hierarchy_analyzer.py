"""
Document Hierarchy Analyzer
전력시장 문서의 구조와 계층을 정밀 분석
"""

import logging
import re
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """문서 유형"""
    REGULATION = "regulation"  # 규칙, 법령
    NOTICE = "notice"  # 고시, 공고
    PROCEDURE = "procedure"  # 절차, 매뉴얼
    TECHNICAL_STANDARD = "technical_standard"  # 기술기준
    CONTRACT = "contract"  # 계약, 협약
    REPORT = "report"  # 보고서
    OTHER = "other"


class HierarchyLevel(Enum):
    """계층 레벨"""
    CHAPTER = "chapter"  # 장
    SECTION = "section"  # 절
    ARTICLE = "article"  # 조
    PARAGRAPH = "paragraph"  # 항
    ITEM = "item"  # 호
    SUBITEM = "subitem"  # 목
    ANNEX = "annex"  # 별표, 부록


@dataclass
class HierarchyNode:
    """계층 구조 노드"""
    level: HierarchyLevel
    number: str  # 번호 (예: "1", "2.1", "제3조")
    title: str  # 제목
    content: str  # 내용
    parent: Optional['HierarchyNode'] = None
    children: List['HierarchyNode'] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}
    
    def add_child(self, child: 'HierarchyNode'):
        """자식 노드 추가"""
        child.parent = self
        self.children.append(child)
    
    def get_full_path(self) -> str:
        """전체 경로 반환 (루트부터 현재까지)"""
        path = []
        current = self
        while current:
            if current.number:
                path.append(current.number)
            current = current.parent
        return " > ".join(reversed(path))
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "level": self.level.value,
            "number": self.number,
            "title": self.title,
            "content": self.content,
            "full_path": self.get_full_path(),
            "children_count": len(self.children),
            "metadata": self.metadata
        }


class DocumentHierarchyAnalyzer:
    """
    문서 계층 구조 분석기
    - 전력시장 문서의 법적/기술적 구조 파악
    - 조항, 별표, 부록 등의 관계 매핑
    - AI가 활용하기 쉬운 구조화된 정보 제공
    """
    
    def __init__(self):
        self.document_patterns = self._initialize_patterns()
        self.hierarchy_rules = self._initialize_hierarchy_rules()
    
    def _initialize_patterns(self) -> Dict[str, List[str]]:
        """문서 패턴 초기화"""
        return {
            # 법령/규칙 패턴
            "legal_article": [
                r"제\s*(\d+)\s*조\s*(\([^)]+\))?\s*(.+)",  # 제1조, 제1조(정의)
                r"제\s*(\d+)\s*조의\s*(\d+)\s*(.+)",  # 제1조의2
            ],
            "legal_paragraph": [
                r"①\s*(.+)",  # 항
                r"②\s*(.+)",
                r"③\s*(.+)",
                r"④\s*(.+)",
                r"⑤\s*(.+)",
                r"⑥\s*(.+)",
                r"⑦\s*(.+)",
                r"⑧\s*(.+)",
                r"⑨\s*(.+)",
                r"⑩\s*(.+)",
            ],
            "legal_item": [
                r"(\d+)\.\s*(.+)",  # 1. 항목
                r"([가-힣])\.\s*(.+)",  # 가. 항목
                r"([ㄱ-ㅎ])\.\s*(.+)",  # ㄱ. 항목
            ],
            
            # 기술문서 패턴
            "chapter": [
                r"제\s*(\d+)\s*장\s+(.+)",  # 제1장
                r"(\d+)\.\s*([^.]+)$",  # 1. 제목 (단독 줄)
            ],
            "section": [
                r"제\s*(\d+)\s*절\s+(.+)",  # 제1절
                r"(\d+)\.(\d+)\s+(.+)",  # 1.1 제목
            ],
            "subsection": [
                r"(\d+)\.(\d+)\.(\d+)\s+(.+)",  # 1.1.1 제목
            ],
            
            # 별표/부록 패턴
            "annex": [
                r"별표\s*(\d+)\s*(.+)",  # 별표1
                r"부록\s*([A-Z]|\d+)\s*(.+)",  # 부록A, 부록1
                r"\[별첨\s*(\d+)\]\s*(.+)",  # [별첨1]
            ],
            
            # 목록 패턴
            "bullet_list": [
                r"[•·▪▫]\s*(.+)",  # 불릿 포인트
                r"[-‐−–—]\s*(.+)",  # 대시
            ],
            "numbered_list": [
                r"(\d+)\)\s*(.+)",  # 1) 항목
                r"\((\d+)\)\s*(.+)",  # (1) 항목
            ]
        }
    
    def _initialize_hierarchy_rules(self) -> Dict[str, Any]:
        """계층 규칙 초기화"""
        return {
            "legal_hierarchy": [
                HierarchyLevel.CHAPTER,   # 장
                HierarchyLevel.SECTION,   # 절  
                HierarchyLevel.ARTICLE,   # 조
                HierarchyLevel.PARAGRAPH, # 항
                HierarchyLevel.ITEM,      # 호
                HierarchyLevel.SUBITEM    # 목
            ],
            "technical_hierarchy": [
                HierarchyLevel.CHAPTER,   # 1.
                HierarchyLevel.SECTION,   # 1.1
                HierarchyLevel.ARTICLE,   # 1.1.1
                HierarchyLevel.PARAGRAPH, # 1.1.1.1
            ]
        }
    
    def analyze_document_structure(self, processed_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        문서 구조 분석
        
        Args:
            processed_doc: MultimodalProcessor에서 처리된 문서
            
        Returns:
            구조화된 계층 정보
        """
        logger.info(f"문서 구조 분석 시작: {processed_doc.get('document_id', 'unknown')}")
        
        try:
            content = processed_doc.get("content", {})
            document_text = content.get("document", "")
            
            # 1. 문서 유형 분류
            doc_type = self._classify_document_type(document_text)
            
            # 2. 계층 구조 추출
            hierarchy_tree = self._extract_hierarchy(document_text, doc_type)
            
            # 3. 구조 메타데이터 생성
            structure_metadata = self._generate_structure_metadata(hierarchy_tree, doc_type)
            
            # 4. 연관성 매핑
            relationships = self._extract_structural_relationships(hierarchy_tree)
            
            result = {
                "document_id": processed_doc.get("document_id"),
                "document_type": doc_type.value,
                "hierarchy_tree": self._serialize_hierarchy_tree(hierarchy_tree),
                "structure_metadata": structure_metadata,
                "relationships": relationships,
                "analysis_timestamp": self._get_timestamp()
            }
            
            logger.info(f"문서 구조 분석 완료: {len(hierarchy_tree)} 노드")
            return result
            
        except Exception as e:
            logger.error(f"문서 구조 분석 실패: {e}")
            return self._create_error_result(processed_doc, str(e))
    
    def _classify_document_type(self, document_text: str) -> DocumentType:
        """문서 유형 분류"""
        type_indicators = {
            DocumentType.REGULATION: ["규칙", "법", "조례", "시행령", "시행규칙"],
            DocumentType.NOTICE: ["고시", "공고", "알림", "시행"],
            DocumentType.PROCEDURE: ["절차", "매뉴얼", "가이드", "지침"],
            DocumentType.TECHNICAL_STANDARD: ["기술기준", "표준", "규격", "사양"],
            DocumentType.CONTRACT: ["계약", "협약", "약정", "합의"],
            DocumentType.REPORT: ["보고서", "분석", "현황", "통계"]
        }
        
        scores = {}
        for doc_type, indicators in type_indicators.items():
            score = sum(1 for indicator in indicators if indicator in document_text)
            scores[doc_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        return DocumentType.OTHER
    
    def _extract_hierarchy(self, document_text: str, doc_type: DocumentType) -> List[HierarchyNode]:
        """계층 구조 추출"""
        hierarchy_tree = []
        lines = document_text.split('\n')
        
        current_chapter = None
        current_section = None
        current_article = None
        current_paragraph = None
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 각 패턴에 대해 매칭 시도
            node = self._match_hierarchy_patterns(line, line_num)
            
            if node:
                # 계층에 따라 부모-자식 관계 설정
                if node.level == HierarchyLevel.CHAPTER:
                    current_chapter = node
                    hierarchy_tree.append(node)
                    current_section = None
                    current_article = None
                    current_paragraph = None
                    
                elif node.level == HierarchyLevel.SECTION:
                    current_section = node
                    if current_chapter:
                        current_chapter.add_child(node)
                    else:
                        hierarchy_tree.append(node)
                    current_article = None
                    current_paragraph = None
                    
                elif node.level == HierarchyLevel.ARTICLE:
                    current_article = node
                    if current_section:
                        current_section.add_child(node)
                    elif current_chapter:
                        current_chapter.add_child(node)
                    else:
                        hierarchy_tree.append(node)
                    current_paragraph = None
                    
                elif node.level == HierarchyLevel.PARAGRAPH:
                    current_paragraph = node
                    if current_article:
                        current_article.add_child(node)
                    elif current_section:
                        current_section.add_child(node)
                    elif current_chapter:
                        current_chapter.add_child(node)
                    else:
                        hierarchy_tree.append(node)
                        
                elif node.level == HierarchyLevel.ITEM:
                    if current_paragraph:
                        current_paragraph.add_child(node)
                    elif current_article:
                        current_article.add_child(node)
                    elif current_section:
                        current_section.add_child(node)
                    else:
                        hierarchy_tree.append(node)
                        
                elif node.level == HierarchyLevel.ANNEX:
                    hierarchy_tree.append(node)  # 별표/부록은 최상위
            else:
                # 패턴에 매칭되지 않는 경우, 현재 활성 노드에 내용 추가
                if current_paragraph:
                    current_paragraph.content += "\n" + line
                elif current_article:
                    current_article.content += "\n" + line
                elif current_section:
                    current_section.content += "\n" + line
                elif current_chapter:
                    current_chapter.content += "\n" + line
        
        return hierarchy_tree
    
    def _match_hierarchy_patterns(self, line: str, line_num: int) -> Optional[HierarchyNode]:
        """텍스트 라인을 계층 패턴과 매칭"""
        
        # 법령 조항 패턴
        for pattern in self.document_patterns["legal_article"]:
            match = re.match(pattern, line)
            if match:
                number = match.group(1)
                title = match.group(3) if len(match.groups()) >= 3 else ""
                return HierarchyNode(
                    level=HierarchyLevel.ARTICLE,
                    number=f"제{number}조",
                    title=title,
                    content=line,
                    metadata={"line_number": line_num, "pattern_type": "legal_article"}
                )
        
        # 법령 항 패턴
        for pattern in self.document_patterns["legal_paragraph"]:
            match = re.match(pattern, line)
            if match:
                content = match.group(1)
                return HierarchyNode(
                    level=HierarchyLevel.PARAGRAPH,
                    number=line[0],  # ①, ②, ③
                    title="",
                    content=content,
                    metadata={"line_number": line_num, "pattern_type": "legal_paragraph"}
                )
        
        # 장 패턴
        for pattern in self.document_patterns["chapter"]:
            match = re.match(pattern, line)
            if match:
                if "제" in pattern:  # 제1장 형태
                    number = match.group(1)
                    title = match.group(2)
                    return HierarchyNode(
                        level=HierarchyLevel.CHAPTER,
                        number=f"제{number}장",
                        title=title,
                        content=line,
                        metadata={"line_number": line_num, "pattern_type": "chapter"}
                    )
                else:  # 1. 형태
                    number = match.group(1)
                    title = match.group(2)
                    return HierarchyNode(
                        level=HierarchyLevel.CHAPTER,
                        number=number,
                        title=title,
                        content=line,
                        metadata={"line_number": line_num, "pattern_type": "chapter"}
                    )
        
        # 절 패턴
        for pattern in self.document_patterns["section"]:
            match = re.match(pattern, line)
            if match:
                if "제" in pattern:  # 제1절 형태
                    number = match.group(1)
                    title = match.group(2)
                    return HierarchyNode(
                        level=HierarchyLevel.SECTION,
                        number=f"제{number}절",
                        title=title,
                        content=line,
                        metadata={"line_number": line_num, "pattern_type": "section"}
                    )
                else:  # 1.1 형태
                    number = f"{match.group(1)}.{match.group(2)}"
                    title = match.group(3)
                    return HierarchyNode(
                        level=HierarchyLevel.SECTION,
                        number=number,
                        title=title,
                        content=line,
                        metadata={"line_number": line_num, "pattern_type": "section"}
                    )
        
        # 별표/부록 패턴
        for pattern in self.document_patterns["annex"]:
            match = re.match(pattern, line)
            if match:
                number = match.group(1)
                title = match.group(2) if len(match.groups()) >= 2 else ""
                return HierarchyNode(
                    level=HierarchyLevel.ANNEX,
                    number=number,
                    title=title,
                    content=line,
                    metadata={"line_number": line_num, "pattern_type": "annex"}
                )
        
        # 번호 매기기 패턴
        for pattern in self.document_patterns["legal_item"]:
            match = re.match(pattern, line)
            if match:
                number = match.group(1)
                content = match.group(2)
                return HierarchyNode(
                    level=HierarchyLevel.ITEM,
                    number=number,
                    title="",
                    content=content,
                    metadata={"line_number": line_num, "pattern_type": "legal_item"}
                )
        
        return None
    
    def _generate_structure_metadata(self, hierarchy_tree: List[HierarchyNode], doc_type: DocumentType) -> Dict[str, Any]:
        """구조 메타데이터 생성"""
        
        def count_nodes_by_level(nodes: List[HierarchyNode]) -> Dict[str, int]:
            counts = {}
            for node in nodes:
                level = node.level.value
                counts[level] = counts.get(level, 0) + 1
                # 재귀적으로 자식 노드들도 계산
                child_counts = count_nodes_by_level(node.children)
                for child_level, count in child_counts.items():
                    counts[child_level] = counts.get(child_level, 0) + count
            return counts
        
        node_counts = count_nodes_by_level(hierarchy_tree)
        
        return {
            "document_type": doc_type.value,
            "total_nodes": sum(node_counts.values()),
            "node_counts_by_level": node_counts,
            "max_depth": self._calculate_max_depth(hierarchy_tree),
            "has_annexes": "annex" in node_counts,
            "structure_complexity": self._assess_structure_complexity(node_counts),
            "hierarchy_patterns": list(set(
                node.metadata.get("pattern_type", "unknown") 
                for node in self._flatten_hierarchy(hierarchy_tree)
            ))
        }
    
    def _calculate_max_depth(self, hierarchy_tree: List[HierarchyNode]) -> int:
        """최대 깊이 계산"""
        if not hierarchy_tree:
            return 0
        
        max_depth = 1
        for node in hierarchy_tree:
            if node.children:
                child_depth = 1 + self._calculate_max_depth(node.children)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _assess_structure_complexity(self, node_counts: Dict[str, int]) -> str:
        """구조 복잡도 평가"""
        total_nodes = sum(node_counts.values())
        level_diversity = len(node_counts)
        
        if total_nodes > 50 and level_diversity > 4:
            return "complex"
        elif total_nodes > 20 and level_diversity > 3:
            return "moderate"
        else:
            return "simple"
    
    def _flatten_hierarchy(self, hierarchy_tree: List[HierarchyNode]) -> List[HierarchyNode]:
        """계층 구조를 평면 리스트로 변환"""
        flattened = []
        for node in hierarchy_tree:
            flattened.append(node)
            flattened.extend(self._flatten_hierarchy(node.children))
        return flattened
    
    def _extract_structural_relationships(self, hierarchy_tree: List[HierarchyNode]) -> List[Dict[str, Any]]:
        """구조적 관계 추출"""
        relationships = []
        
        # 계층 관계 (부모-자식)
        for node in self._flatten_hierarchy(hierarchy_tree):
            if node.parent:
                relationships.append({
                    "type": "hierarchical",
                    "source": node.parent.get_full_path(),
                    "target": node.get_full_path(),
                    "relationship": "parent_child"
                })
            
            # 형제 관계
            if node.parent:
                siblings = [child for child in node.parent.children if child != node]
                for sibling in siblings:
                    relationships.append({
                        "type": "hierarchical",
                        "source": node.get_full_path(),
                        "target": sibling.get_full_path(),
                        "relationship": "sibling"
                    })
        
        # 참조 관계 (본문에서 다른 조항 참조)
        for node in self._flatten_hierarchy(hierarchy_tree):
            content = node.content
            ref_patterns = [
                r"제\s*(\d+)\s*조",
                r"별표\s*(\d+)",
                r"부록\s*([A-Z]|\d+)",
                r"(\d+)\.(\d+)\.(\d+)"
            ]
            
            for pattern in ref_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    relationships.append({
                        "type": "reference",
                        "source": node.get_full_path(),
                        "target": str(match),
                        "relationship": "references"
                    })
        
        return relationships
    
    def _serialize_hierarchy_tree(self, hierarchy_tree: List[HierarchyNode]) -> List[Dict[str, Any]]:
        """계층 트리를 직렬화"""
        serialized = []
        
        for node in hierarchy_tree:
            node_dict = node.to_dict()
            if node.children:
                node_dict["children"] = self._serialize_hierarchy_tree(node.children)
            serialized.append(node_dict)
        
        return serialized
    
    def _get_timestamp(self) -> str:
        """현재 타임스탬프"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _create_error_result(self, processed_doc: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """오류 결과 생성"""
        return {
            "document_id": processed_doc.get("document_id", "unknown"),
            "document_type": DocumentType.OTHER.value,
            "hierarchy_tree": [],
            "structure_metadata": {},
            "relationships": [],
            "error": error_msg,
            "analysis_timestamp": self._get_timestamp()
        }
    
    def extract_contextual_chunks(self, hierarchy_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        계층 분석 결과를 기반으로 맥락을 고려한 청크 생성
        - 구조적 경계를 존중
        - 상위 컨텍스트 정보 포함
        - AI가 이해하기 쉬운 형태로 구성
        """
        chunks = []
        hierarchy_tree = hierarchy_analysis.get("hierarchy_tree", [])
        
        def create_chunks_from_nodes(nodes: List[Dict[str, Any]], parent_context: str = ""):
            for node in nodes:
                # 현재 노드의 컨텍스트 생성
                current_context = parent_context
                if node.get("title"):
                    current_context += f" > {node['title']}"
                
                # 청크 생성
                chunk = {
                    "text": node.get("content", ""),
                    "hierarchy_level": node.get("level"),
                    "hierarchy_number": node.get("number"),
                    "hierarchy_title": node.get("title"),
                    "full_path": node.get("full_path"),
                    "parent_context": parent_context.strip(" > "),
                    "structural_metadata": {
                        "children_count": node.get("children_count", 0),
                        "has_children": node.get("children_count", 0) > 0,
                        "depth_level": current_context.count(">") + 1
                    }
                }
                
                # 내용이 있는 경우에만 청크 추가
                if chunk["text"] and chunk["text"].strip():
                    chunks.append(chunk)
                
                # 자식 노드들 처리
                children = node.get("children", [])
                if children:
                    create_chunks_from_nodes(children, current_context)
        
        create_chunks_from_nodes(hierarchy_tree)
        return chunks
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """분석 통계 정보"""
        return {
            "supported_document_types": [dt.value for dt in DocumentType],
            "supported_hierarchy_levels": [hl.value for hl in HierarchyLevel],
            "pattern_categories": list(self.document_patterns.keys()),
            "total_patterns": sum(len(patterns) for patterns in self.document_patterns.values())
        }


def get_document_hierarchy_analyzer() -> DocumentHierarchyAnalyzer:
    """Document Hierarchy Analyzer 싱글톤 인스턴스 반환"""
    if not hasattr(get_document_hierarchy_analyzer, "_instance"):
        get_document_hierarchy_analyzer._instance = DocumentHierarchyAnalyzer()
    return get_document_hierarchy_analyzer._instance