"""
멀티모달 문서 처리기
텍스트, 이미지, 표, 수식을 통합적으로 처리하여 AI가 활용할 수 있는 형태로 변환
"""

import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path
import json
import base64
from datetime import datetime
import re
import io

# PDF 처리
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# PyPDF2는 선택적으로 사용
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# 이미지 처리
try:
    import cv2
    import numpy as np
    from PIL import Image
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False

# OCR
try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# 표 추출
try:
    import pandas as pd
    import tabula
    TABLE_AVAILABLE = True
except ImportError:
    TABLE_AVAILABLE = False

logger = logging.getLogger(__name__)


class MultimodalProcessor:
    """
    멀티모달 문서 처리기
    
    기능:
    - PDF 고급 파싱 (텍스트, 이미지, 표, 수식 분리)
    - 이미지 분석 및 OCR
    - 표 구조화
    - 수식 인식 및 LaTeX 변환
    - 문서 구조 분석 (제목, 섹션, 문단)
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.documents_dir = self.data_dir / "documents"
        self.processed_dir = self.data_dir / "processed"
        
        # 디렉토리 생성
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # OCR 초기화
        self.ocr_reader = None
        if OCR_AVAILABLE:
            try:
                self.ocr_reader = easyocr.Reader(['ko', 'en'])
                logger.info("OCR 리더 초기화 완료")
            except Exception as e:
                logger.warning(f"OCR 리더 초기화 실패: {e}")
        
        # 처리 통계
        self.processing_stats = {
            "total_documents": 0,
            "processed_documents": 0,
            "extracted_images": 0,
            "extracted_tables": 0,
            "extracted_formulas": 0
        }
    
    def process_document(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        문서 전체 처리
        
        Args:
            file_path: 처리할 문서 파일 경로
            
        Returns:
            계층적으로 구조화된 문서 데이터
        """
        file_path = Path(file_path)
        logger.info(f"문서 처리 시작: {file_path.name}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
        try:
            # 파일 타입별 처리
            if file_path.suffix.lower() == '.pdf':
                return self._process_pdf(file_path)
            else:
                logger.warning(f"지원하지 않는 파일 타입: {file_path.suffix}")
                return self._create_empty_result(file_path)
                
        except Exception as e:
            logger.error(f"문서 처리 실패 {file_path.name}: {e}")
            return self._create_error_result(file_path, str(e))
    
    def _process_pdf(self, file_path: Path) -> Dict[str, Any]:
        """PDF 파일 고급 처리"""
        result = {
            "document_id": file_path.stem,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "processed_at": datetime.now().isoformat(),
            "content": {
                "document": "",
                "sections": [],
                "paragraphs": [],
                "sentences": []
            },
            "multimodal_content": {
                "images": [],
                "tables": [],
                "formulas": []
            },
            "metadata": {
                "total_pages": 0,
                "processing_time_ms": 0,
                "structure": {}
            }
        }
        
        start_time = datetime.now()
        
        try:
            # PyMuPDF로 처리 (이미지, 표 추출 가능)
            if PDF_AVAILABLE:
                doc = fitz.open(file_path)
                result["metadata"]["total_pages"] = len(doc)
                
                full_text = ""
                sections = []
                paragraphs = []
                images = []
                tables = []
                
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    
                    # 텍스트 추출
                    page_text = page.get_text()
                    full_text += page_text + "\n"
                    
                    # 이미지 추출
                    page_images = self._extract_images_from_page(page, page_num)
                    images.extend(page_images)
                    
                    # 표 추출 시도
                    page_tables = self._extract_tables_from_page(page, page_num)
                    tables.extend(page_tables)
                    
                    # 페이지별 문단 분석
                    page_paragraphs = self._analyze_paragraphs(page_text, page_num)
                    paragraphs.extend(page_paragraphs)
                
                doc.close()
                
                # 문서 구조 분석
                sections = self._analyze_document_structure(full_text)
                sentences = self._extract_sentences(paragraphs)
                
                # 결과 구성
                result["content"]["document"] = full_text.strip()
                result["content"]["sections"] = sections
                result["content"]["paragraphs"] = paragraphs
                result["content"]["sentences"] = sentences
                result["multimodal_content"]["images"] = images
                result["multimodal_content"]["tables"] = tables
                
                # 수식 추출
                formulas = self._extract_formulas(full_text)
                result["multimodal_content"]["formulas"] = formulas
                
        except Exception as e:
            logger.error(f"PDF 처리 중 오류: {e}")
            result["error"] = str(e)
        
        # 처리 시간 기록
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        result["metadata"]["processing_time_ms"] = processing_time
        
        # 통계 업데이트
        self.processing_stats["total_documents"] += 1
        self.processing_stats["processed_documents"] += 1
        self.processing_stats["extracted_images"] += len(result["multimodal_content"]["images"])
        self.processing_stats["extracted_tables"] += len(result["multimodal_content"]["tables"])
        self.processing_stats["extracted_formulas"] += len(result["multimodal_content"]["formulas"])
        
        logger.info(f"PDF 처리 완료: {file_path.name} ({processing_time:.2f}ms)")
        return result
    
    def _extract_images_from_page(self, page, page_num: int) -> List[Dict[str, Any]]:
        """페이지에서 이미지 추출"""
        images = []
        
        try:
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    # 이미지 정보 추출
                    xref = img[0]
                    pix = fitz.Pixmap(page.parent, xref)
                    
                    if pix.n < 5:  # GRAY or RGB
                        # 이미지를 bytes로 변환
                        img_data = pix.tobytes("png")
                        
                        # Base64 인코딩 (필요시)
                        img_base64 = base64.b64encode(img_data).decode()
                        
                        # OCR 수행 (가능한 경우)
                        ocr_text = ""
                        if self.ocr_reader and len(img_data) < 5 * 1024 * 1024:  # 5MB 미만만
                            try:
                                # PIL Image로 변환하여 OCR
                                pil_img = Image.open(io.BytesIO(img_data))
                                ocr_results = self.ocr_reader.readtext(np.array(pil_img))
                                ocr_text = " ".join([result[1] for result in ocr_results])
                            except Exception as e:
                                logger.debug(f"OCR 실패 (페이지 {page_num}, 이미지 {img_index}): {e}")
                        
                        images.append({
                            "page_number": page_num,
                            "image_index": img_index,
                            "width": pix.width,
                            "height": pix.height,
                            "size_bytes": len(img_data),
                            "ocr_text": ocr_text,
                            "description": self._generate_image_description(ocr_text, pix.width, pix.height),
                            "base64_data": img_base64[:1000] + "..." if len(img_base64) > 1000 else img_base64  # 샘플만
                        })
                    
                    pix = None
                    
                except Exception as e:
                    logger.debug(f"이미지 처리 실패 (페이지 {page_num}, 이미지 {img_index}): {e}")
                    
        except Exception as e:
            logger.debug(f"페이지 {page_num} 이미지 추출 실패: {e}")
        
        return images
    
    def _extract_tables_from_page(self, page, page_num: int) -> List[Dict[str, Any]]:
        """페이지에서 표 추출"""
        tables = []
        
        try:
            # PyMuPDF의 테이블 감지 시도
            page_tables = page.find_tables()
            
            for table_index, table in enumerate(page_tables):
                try:
                    # 표 데이터 추출
                    table_data = table.extract()
                    
                    if table_data and len(table_data) > 1:  # 최소 2행 이상
                        # 표를 구조화된 형태로 변환
                        structured_table = {
                            "page_number": page_num,
                            "table_index": table_index,
                            "rows": len(table_data),
                            "columns": len(table_data[0]) if table_data else 0,
                            "headers": table_data[0] if table_data else [],
                            "data": table_data[1:] if len(table_data) > 1 else [],
                            "bbox": table.bbox,  # 경계 상자
                            "description": self._generate_table_description(table_data)
                        }
                        
                        tables.append(structured_table)
                        
                except Exception as e:
                    logger.debug(f"표 처리 실패 (페이지 {page_num}, 표 {table_index}): {e}")
                    
        except Exception as e:
            logger.debug(f"페이지 {page_num} 표 추출 실패: {e}")
        
        return tables
    
    def _analyze_document_structure(self, text: str) -> List[Dict[str, Any]]:
        """문서 구조 분석 (섹션, 제목 등)"""
        sections = []
        
        # 간단한 섹션 분석 (개선 필요)
        lines = text.split('\n')
        current_section = None
        section_content = []
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            if not line:
                continue
            
            # 제목으로 보이는 패턴 감지
            if self._is_section_title(line):
                # 이전 섹션 저장
                if current_section and section_content:
                    current_section["content"] = "\n".join(section_content)
                    current_section["word_count"] = len(current_section["content"].split())
                    sections.append(current_section)
                
                # 새 섹션 시작
                current_section = {
                    "title": line,
                    "section_index": len(sections),
                    "line_number": line_num,
                    "content": "",
                    "subsections": []
                }
                section_content = []
            else:
                if current_section:
                    section_content.append(line)
        
        # 마지막 섹션 저장
        if current_section and section_content:
            current_section["content"] = "\n".join(section_content)
            current_section["word_count"] = len(current_section["content"].split())
            sections.append(current_section)
        
        return sections
    
    def _is_section_title(self, line: str) -> bool:
        """섹션 제목인지 판단"""
        # 전력시장 문서의 일반적인 패턴들
        patterns = [
            r'^제\s*\d+\s*[조항호]',  # 제1조, 제2항 등
            r'^\d+\.\s+',  # 1. 2. 3. 등
            r'^[가-힣]+\s*\d+\s*[조항호]',  # 부칙 제1조 등
            r'^별표\s*\d+',  # 별표 1
            r'^부록\s*\d*',  # 부록
            r'^[가-힣]{2,}\s*절차',  # ~절차
            r'^[가-힣]{2,}\s*기준',  # ~기준
            r'^[가-힣]{2,}\s*규칙',  # ~규칙
        ]
        
        for pattern in patterns:
            if re.match(pattern, line):
                return True
        
        # 길이가 짧고 마침표로 끝나지 않는 경우도 제목일 가능성
        if len(line) < 50 and not line.endswith('.') and not line.endswith(','):
            # 한글/영문/숫자/공백/특수문자만 포함하고 비교적 간결한 경우
            if re.match(r'^[가-힣a-zA-Z0-9\s\-()]+$', line):
                return True
        
        return False
    
    def _analyze_paragraphs(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """문단 분석"""
        paragraphs = []
        
        # 빈 줄로 문단 구분
        raw_paragraphs = text.split('\n\n')
        
        for para_index, para_text in enumerate(raw_paragraphs):
            para_text = para_text.strip()
            
            if para_text and len(para_text) > 10:  # 너무 짧은 것은 제외
                paragraphs.append({
                    "content": para_text,
                    "paragraph_index": para_index,
                    "page_number": page_num,
                    "word_count": len(para_text.split()),
                    "char_count": len(para_text),
                    "sentences_count": len(re.split(r'[.!?]+', para_text))
                })
        
        return paragraphs
    
    def _extract_sentences(self, paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """문장 추출"""
        sentences = []
        sentence_index = 0
        
        for para in paragraphs:
            content = para["content"]
            
            # 문장 분리 (간단한 방법, 개선 필요)
            raw_sentences = re.split(r'[.!?]+', content)
            
            for sent_text in raw_sentences:
                sent_text = sent_text.strip()
                
                if sent_text and len(sent_text) > 5:  # 너무 짧은 것은 제외
                    sentences.append({
                        "content": sent_text,
                        "sentence_index": sentence_index,
                        "paragraph_id": f"para_{para['paragraph_index']}",
                        "page_number": para["page_number"],
                        "char_count": len(sent_text)
                    })
                    sentence_index += 1
        
        return sentences
    
    def _extract_formulas(self, text: str) -> List[Dict[str, Any]]:
        """수식 추출"""
        formulas = []
        
        # 간단한 수식 패턴 감지
        formula_patterns = [
            r'[A-Za-z]+\s*[=]\s*[^가-힣\n]{3,}',  # 변수 = 수식
            r'\d+[.]?\d*\s*[×÷+-]\s*\d+[.]?\d*',  # 산술식
            r'[∫∑∏√±≤≥≠≈]',  # 수학 기호
            r'[A-Za-z]+\s*[₀₁₂₃₄₅₆₇₈₉]+',  # 하첨자
            r'[A-Za-z]+\s*[⁰¹²³⁴⁵⁶⁷⁸⁹]+',  # 상첨자
        ]
        
        for pattern in formula_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                formula_text = match.group()
                
                formulas.append({
                    "formula": formula_text,
                    "start_pos": match.start(),
                    "end_pos": match.end(),
                    "context": text[max(0, match.start()-50):match.end()+50],
                    "type": "mathematical_expression",
                    "description": f"수학적 표현: {formula_text}"
                })
        
        return formulas
    
    def _generate_image_description(self, ocr_text: str, width: int, height: int) -> str:
        """이미지 설명 생성"""
        description = f"이미지 (크기: {width}x{height})"
        
        if ocr_text:
            description += f" - OCR 텍스트: {ocr_text[:100]}{'...' if len(ocr_text) > 100 else ''}"
        
        # 크기로 이미지 타입 추정
        if width > height * 2:
            description += " (가로형, 도표/차트 가능성)"
        elif height > width * 2:
            description += " (세로형, 텍스트 이미지 가능성)"
        else:
            description += " (정방형, 아이콘/로고 가능성)"
        
        return description
    
    def _generate_table_description(self, table_data: List[List]) -> str:
        """표 설명 생성"""
        if not table_data:
            return "빈 표"
        
        rows = len(table_data)
        cols = len(table_data[0]) if table_data else 0
        
        description = f"표 ({rows}행 x {cols}열)"
        
        # 헤더 정보 추가
        if table_data and table_data[0]:
            headers = [str(h) for h in table_data[0] if h]
            if headers:
                description += f" - 헤더: {', '.join(headers[:3])}{'...' if len(headers) > 3 else ''}"
        
        return description
    
    def _create_empty_result(self, file_path: Path) -> Dict[str, Any]:
        """빈 결과 구조 생성"""
        return {
            "document_id": file_path.stem,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "processed_at": datetime.now().isoformat(),
            "content": {
                "document": "",
                "sections": [],
                "paragraphs": [],
                "sentences": []
            },
            "multimodal_content": {
                "images": [],
                "tables": [],
                "formulas": []
            },
            "metadata": {
                "total_pages": 0,
                "processing_time_ms": 0,
                "error": "지원하지 않는 파일 형식"
            }
        }
    
    def _create_error_result(self, file_path: Path, error_msg: str) -> Dict[str, Any]:
        """오류 결과 구조 생성"""
        result = self._create_empty_result(file_path)
        result["metadata"]["error"] = error_msg
        return result
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """처리 통계 반환"""
        return {
            **self.processing_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_processed_document(self, processed_data: Dict[str, Any]) -> bool:
        """처리된 문서 데이터 저장"""
        try:
            doc_id = processed_data["document_id"]
            output_file = self.processed_dir / f"{doc_id}_processed.json"
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"처리된 문서 저장 완료: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"처리된 문서 저장 실패: {e}")
            return False


def get_multimodal_processor(data_dir: str = "data") -> MultimodalProcessor:
    """멀티모달 프로세서 싱글톤 인스턴스 반환"""
    if not hasattr(get_multimodal_processor, "_instance"):
        get_multimodal_processor._instance = MultimodalProcessor(data_dir=data_dir)
    return get_multimodal_processor._instance