"""
실제 별표 33 정산 공식 추출기
제주 시범사업의 급전가능재생에너지자원 및 급전가능집합전력자원 정산 공식
"""

import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class FormulaVariable:
    """정산 공식 변수 정의"""
    symbol: str
    name: str
    unit: str
    description: str
    decimal_places: Optional[int] = None
    constraints: Optional[str] = None


@dataclass
class SettlementFormula:
    """정산 공식 정의"""
    formula_id: str
    name: str
    category: str  # 에너지정산금, 변동비보전정산금, 기대이익정산금 등
    resource_type: str  # 급전가능재생에너지자원, 급전가능집합전력자원
    formula_text: str
    variables: List[FormulaVariable]
    calculation_steps: List[str]
    conditions: List[str]
    decimal_handling: Dict[str, int]


class ActualFormulaExtractor:
    """
    별표 33의 실제 정산 공식 추출 및 구조화
    """
    
    def __init__(self):
        self.formulas = {}
        self.variables = {}
        self._initialize_actual_formulas()
    
    def _initialize_actual_formulas(self):
        """별표 33에서 추출한 실제 정산 공식들 초기화"""
        
        # 1. 급전가능재생에너지자원 에너지정산금
        renewable_energy_settlement = SettlementFormula(
            formula_id="renewable_energy_settlement",
            name="급전가능재생에너지자원 에너지정산금",
            category="에너지정산금",
            resource_type="급전가능재생에너지자원",
            formula_text="MEPi,t = DA_MEP i,t + ∑q RT_MEP i,t,q",
            variables=[
                FormulaVariable("MEPi,t", "에너지정산금", "원", "급전가능재생에너지자원(i)의 거래시간(t)별 에너지정산금"),
                FormulaVariable("DA_MEP i,t", "하루전에너지정산금", "원", "급전가능재생에너지자원(i)의 거래시간(t)별 하루전에너지시장 에너지정산금"),
                FormulaVariable("RT_MEP i,t,q", "실시간에너지정산금", "원", "급전가능재생에너지자원(i)의 거래시간(t) 내 구간(q)별 실시간에너지시장 에너지정산금")
            ],
            calculation_steps=[
                "1. 하루전에너지정산금 계산: DA_MEP i,t = DA_MP i,t × DA_SE i,t × 1h × 1,000",
                "2. 15분 구간별 발전량 비중 계산: TPR_E i,t,q = MGO i,t,q / MGO i,t (∑TPR_E = 1.0)",
                "3. 15분 구간별 실시간정산금 계산: RT_MEP i,t,q = RT_MP i,t,q × (MGO i,t - DA_SE i,t × 1h) × TPR_E i,t,q × 1,000",
                "4. 실시간에너지정산금 = ∑(q=1~4) RT_MEP i,t,q",
                "5. 총 에너지정산금 = 하루전에너지정산금 + 실시간에너지정산금"
            ],
            conditions=[
                "고정가격계약 물량과 그 외 물량으로 구분하여 계산",
                "고정가격계약 물량: Min(EP i,t, UPFP i,j,c,t/1,000) × MGO i,j,t × CR i,j,c,t",
                "그 외 물량: EP i,t × MGO i,j,t × (1 - ∑c CRi,j,c,t)",
                "실시간 정산은 15분 구간별(q=1~4)로 계산하여 합산",
                "t: 거래시간 (예: t=02는 01:00~02:00), q: 15분구간 (q=1~4)"
            ],
            decimal_handling={
                "계량전력량": 3,  # MWh, 소숫점 셋째자리
                "가격": 2,      # 원/kWh, 소숫점 둘째자리
                "비율": 3       # CR 값, 소숫점 셋째자리에서 반올림
            }
        )
        
        # 2. 급전가능재생에너지자원 변동비보전정산금
        renewable_variable_cost_settlement = SettlementFormula(
            formula_id="renewable_variable_cost_settlement",
            name="급전가능재생에너지자원 변동비보전정산금",
            category="변동비보전정산금",
            resource_type="급전가능재생에너지자원",
            formula_text="MWP i,t = Max(SCMWG i,t - MPMWG i,t, 0) × SCMWG_FLAG i,t",
            variables=[
                FormulaVariable("MWP i,t", "변동비보전정산금", "원", "급전가능재생에너지자원(i)의 거래시간(t)별 변동비보전정산금"),
                FormulaVariable("SCMWG i,t", "변동비", "원", "급전가능재생에너지자원(i)의 거래시간(t)별 변동비보전정산금 지급 영역에 대한 변동비"),
                FormulaVariable("MPMWG i,t", "에너지정산금", "원", "급전가능재생에너지자원(i)의 거래시간(t)별 변동비보전정산금 지급 영역에 대한 에너지정산금"),
                FormulaVariable("SCMWG_FLAG i,t", "지급플래그", "0/1", "급전가능재생에너지자원(i)의 거래시간(t)별 변동비보전정산금 지급 플래그")
            ],
            calculation_steps=[
                "1. 변동비 계산: SCMWG i,t = ∑MW RT_OFFER_PRICE i,t(MW) × MWG_UP i,t × 1,000",
                "2. 에너지정산금 계산: MPMWG i,t = DA_MEP i,t + RT_MEP i,t,q",
                "3. 변동비보전정산금 = Max(변동비 - 에너지정산금, 0) × 지급플래그"
            ],
            conditions=[
                "공급가능용량 이내로 발전한 전력량에 대해서만 적용",
                "에너지정산금으로 입찰비용을 회수할 수 없는 경우에만 지급",
                "급전지시로 공급가능용량 초과 발전 시 전체 전력량에 대한 입찰비용 차액 정산"
            ],
            decimal_handling={
                "변동비": 0,     # 원 단위
                "정산금": 0      # 원 단위
            }
        )
        
        # 3. 급전가능재생에너지자원 기대이익정산금
        renewable_expected_profit_settlement = SettlementFormula(
            formula_id="renewable_expected_profit_settlement",
            name="급전가능재생에너지자원 기대이익정산금",
            category="기대이익정산금",
            resource_type="급전가능재생에너지자원",
            formula_text="MAPi,t = Max(E_MAP i,t - MWP i,t, 0)",
            variables=[
                FormulaVariable("MAPi,t", "기대이익정산금", "원", "급전가능재생에너지자원(i)의 거래시간(t)별 기대이익정산금"),
                FormulaVariable("E_MAP i,t", "에너지기대이익정산금", "원", "급전가능재생에너지자원(i)의 거래시간(t)별 에너지기대이익정산금"),
                FormulaVariable("MWP i,t", "변동비보전정산금", "원", "급전가능재생에너지자원(i)의 거래시간(t)별 변동비보전정산금")
            ],
            calculation_steps=[
                "1. 에너지기대이익정산금 계산: E_MAP i,t = MPMAG i,t - SCMAG i,t",
                "2. 기대이익정산금 = Max(에너지기대이익정산금 - 변동비보전정산금, 0)"
            ],
            conditions=[
                "전력거래소의 급전지시에 의해 하루전에너지계획량과 다르게 운전한 경우",
                "하루전발전계획으로 발전했을 시의 기대이익을 보전하기 위한 목적",
                "허용오차 이내인 경우: |Min(DA_SE i,t × 1h, RA i,t) - MGO i,t| ≤ ε i,t 이면 MAP i,t = 0"
            ],
            decimal_handling={
                "정산금": 0      # 원 단위
            }
        )
        
        # 4. 하루전에너지가격 계산
        day_ahead_energy_price = SettlementFormula(
            formula_id="day_ahead_energy_price",
            name="하루전에너지가격",
            category="가격계산",
            resource_type="급전가능재생에너지자원",
            formula_text="DA_MP i,t = DA_SMP i,t × STLF i,t",
            variables=[
                FormulaVariable("DA_MP i,t", "하루전에너지거래가격", "원/kWh", "급전가능재생에너지자원(i)의 거래시간(t)별 하루전에너지시장 에너지 거래가격"),
                FormulaVariable("DA_SMP i,t", "하루전에너지가격", "원/kWh", "거래시간(t)별 하루전에너지가격"),
                FormulaVariable("STLF i,t", "손실계수", "비율", "급전가능재생에너지자원(i)의 거래시간(t)별 손실계수")
            ],
            calculation_steps=[
                "1. 하루전에너지거래가격 = 하루전에너지가격 × 손실계수"
            ],
            conditions=[
                "손실계수는 송전손실을 반영한 계수"
            ],
            decimal_handling={
                "가격": 4,      # 원/kWh, 소숫점 넷째자리
                "손실계수": 6   # 소숫점 여섯째자리
            }
        )
        
        # 5. 실시간에너지가격 계산
        real_time_energy_price = SettlementFormula(
            formula_id="real_time_energy_price",
            name="실시간에너지가격",
            category="가격계산",
            resource_type="급전가능재생에너지자원",
            formula_text="RT_MP i,t,q = RT_SMP i,t,q × STLF i,t,q",
            variables=[
                FormulaVariable("RT_MP i,t,q", "실시간에너지거래가격", "원/kWh", "급전가능재생에너지자원(i)의 거래시간(t) 내 구간(q)별 실시간에너지시장 에너지 거래가격"),
                FormulaVariable("RT_SMP i,t,q", "실시간에너지가격", "원/kWh", "거래시간(t) 내 구간(q)별 실시간에너지가격"),
                FormulaVariable("STLF i,t,q", "손실계수", "비율", "급전가능재생에너지자원(i)의 거래시간(t) 내 구간(q)별 손실계수")
            ],
            calculation_steps=[
                "1. 실시간에너지거래가격 = 실시간에너지가격 × 손실계수"
            ],
            conditions=[
                "5분 단위 구간별로 계산"
            ],
            decimal_handling={
                "가격": 4,      # 원/kWh, 소숫점 넷째자리
                "손실계수": 6   # 소숫점 여섯째자리
            }
        )
        
        # 6. 급전가능집합전력자원 에너지정산금 (비중앙급전발전기 및 비중앙급전전기저장장치)
        aggregated_energy_settlement = SettlementFormula(
            formula_id="aggregated_energy_settlement",
            name="급전가능집합전력자원 에너지정산금",
            category="에너지정산금",
            resource_type="급전가능집합전력자원",
            formula_text="MEPi,t = DA_MEP i,t + ∑q RT_MEP i,t,q",
            variables=[
                FormulaVariable("MEPi,t", "에너지정산금", "원", "비중앙급전발전기 및 비중앙급전전기저장장치(i)의 거래시간(t)별 에너지정산금"),
                FormulaVariable("DA_MEP i,t", "하루전에너지정산금", "원", "비중앙급전발전기 및 비중앙급전전기저장장치(i)의 거래시간(t)별 하루전에너지시장 에너지정산금"),
                FormulaVariable("RT_MEP i,t,q", "실시간에너지정산금", "원", "비중앙급전발전기 및 비중앙급전전기저장장치(i)의 거래시간(t) 내 구간(q)별 실시간에너지시장 에너지정산금")
            ],
            calculation_steps=[
                "1. 하루전에너지시장 입찰대상 발전기의 경우: DA_MEP i,t = DA_MP i,t × DA_SE i,t × 1,000 × 1h",
                "2. 그 외의 경우: DA_MEP i,t = DA_MP i,t × MGO i,t × 1,000 × 1h",
                "3. 15분 구간별 발전량 비중 계산: TPR_E i,t,q = MGO i,t,q / MGO i,t (∑TPR_E = 1.0)",
                "4. 하루전에너지시장 입찰대상 발전기의 경우: RT_MEP i,t,q = RT_MP i,t,q × (MGO i,t - DA_SE i,t × 1h) × TPR_E i,t,q × 1,000",
                "5. 그 외의 경우: RT_MEP i,t,q = 0",
                "6. 실시간에너지정산금 = ∑(q=1~4) RT_MEP i,t,q",
                "7. 총 에너지정산금 = 하루전에너지정산금 + 실시간에너지정산금"
            ],
            conditions=[
                "급전가능집합전력자원의 보유자원에 해당하는 비중앙급전발전기 및 비중앙급전전기저장장치에 대해서는 정산금을 지급하지 아니함",
                "제16.3.1조의 하루전에너지시장 입찰 대상 여부에 따라 계산 방식이 다름",
                "입찰 대상이 아닌 발전기: 전체 계량전력량을 하루전에너지가격으로 정산",
                "입찰 대상이 아닌 발전기: 실시간에너지시장 정산금은 0",
                "실시간 정산은 15분 구간별(q=1~4)로 계산하여 합산",
                "t: 거래시간 (예: t=02는 01:00~02:00), q: 15분구간 (q=1~4)"
            ],
            decimal_handling={
                "계량전력량": 3,  # MWh, 소숫점 셋째자리
                "가격": 2,       # 원/kWh, 소숫점 둘째자리
                "정산금": 0      # 원 단위
            }
        )
        
        # 7. 급전가능집합전력자원 하루전에너지가격
        aggregated_day_ahead_price = SettlementFormula(
            formula_id="aggregated_day_ahead_price",
            name="급전가능집합전력자원 하루전에너지가격",
            category="가격계산",
            resource_type="급전가능집합전력자원",
            formula_text="DA_MP i,t = DA_SMP i,t × STLF i,t",
            variables=[
                FormulaVariable("DA_MP i,t", "하루전에너지거래가격", "원/kWh", "비중앙급전발전기 및 비중앙급전전기저장장치(i)의 거래시간(t)별 하루전에너지시장 에너지 거래가격"),
                FormulaVariable("DA_SMP i,t", "하루전에너지가격", "원/kWh", "거래시간(t)별 하루전에너지가격"),
                FormulaVariable("STLF i,t", "손실계수", "비율", "비중앙급전발전기 및 비중앙급전전기저장장치(i)의 거래시간(t)별 손실계수")
            ],
            calculation_steps=[
                "1. 하루전에너지거래가격 = 하루전에너지가격 × 손실계수"
            ],
            conditions=[
                "급전가능집합전력자원에 속한 비중앙급전발전기 및 비중앙급전전기저장장치에 적용"
            ],
            decimal_handling={
                "가격": 4,      # 원/kWh, 소숫점 넷째자리
                "손실계수": 6   # 소숫점 여섯째자리
            }
        )
        
        # 8. 급전가능집합전력자원 실시간에너지가격
        aggregated_real_time_price = SettlementFormula(
            formula_id="aggregated_real_time_price",
            name="급전가능집합전력자원 실시간에너지가격",
            category="가격계산",
            resource_type="급전가능집합전력자원",
            formula_text="RT_MP i,t,q = RT_SMP i,t,q × STLF i,t,q",
            variables=[
                FormulaVariable("RT_MP i,t,q", "실시간에너지거래가격", "원/kWh", "비중앙급전발전기 및 비중앙급전전기저장장치(i)의 거래시간(t) 내 구간(q)별 실시간에너지시장 에너지 거래가격"),
                FormulaVariable("RT_SMP i,t,q", "실시간에너지가격", "원/kWh", "거래시간(t) 내 구간(q)별 실시간에너지가격"),
                FormulaVariable("STLF i,t,q", "손실계수", "비율", "비중앙급전발전기 및 비중앙급전전기저장장치(i)의 거래시간(t) 내 구간(q)별 손실계수")
            ],
            calculation_steps=[
                "1. 실시간에너지거래가격 = 실시간에너지가격 × 손실계수"
            ],
            conditions=[
                "하루전에너지시장 입찰대상 발전기에만 적용",
                "입찰 대상이 아닌 발전기는 실시간 정산 없음"
            ],
            decimal_handling={
                "가격": 4,      # 원/kWh, 소숫점 넷째자리
                "손실계수": 6   # 소숫점 여섯째자리
            }
        )
        
        # 공식들을 딕셔너리에 저장
        self.formulas = {
            "renewable_energy_settlement": renewable_energy_settlement,
            "renewable_variable_cost_settlement": renewable_variable_cost_settlement,
            "renewable_expected_profit_settlement": renewable_expected_profit_settlement,
            "day_ahead_energy_price": day_ahead_energy_price,
            "real_time_energy_price": real_time_energy_price,
            "aggregated_energy_settlement": aggregated_energy_settlement,
            "aggregated_day_ahead_price": aggregated_day_ahead_price,
            "aggregated_real_time_price": aggregated_real_time_price
        }
        
        logger.info(f"실제 정산 공식 {len(self.formulas)}개 초기화 완료")
    
    def get_formula(self, formula_id: str) -> Optional[SettlementFormula]:
        """특정 공식 조회"""
        return self.formulas.get(formula_id)
    
    def get_formulas_by_category(self, category: str) -> List[SettlementFormula]:
        """카테고리별 공식 조회"""
        return [formula for formula in self.formulas.values() if formula.category == category]
    
    def get_formulas_by_resource_type(self, resource_type: str) -> List[SettlementFormula]:
        """자원 타입별 공식 조회"""
        return [formula for formula in self.formulas.values() if formula.resource_type == resource_type]
    
    def get_all_variables(self) -> List[FormulaVariable]:
        """모든 변수 조회"""
        all_variables = []
        for formula in self.formulas.values():
            all_variables.extend(formula.variables)
        return all_variables
    
    def search_formulas(self, keyword: str) -> List[SettlementFormula]:
        """키워드로 공식 검색"""
        results = []
        keyword_lower = keyword.lower()
        
        for formula in self.formulas.values():
            if (keyword_lower in formula.name.lower() or 
                keyword_lower in formula.formula_text.lower() or
                any(keyword_lower in var.name.lower() for var in formula.variables)):
                results.append(formula)
        
        return results
    
    def validate_formula_calculation(self, formula_id: str, inputs: Dict[str, float]) -> Dict[str, Any]:
        """공식 계산 검증"""
        formula = self.get_formula(formula_id)
        if not formula:
            return {"error": f"공식을 찾을 수 없습니다: {formula_id}"}
        
        # 필수 변수 확인
        required_vars = [var.symbol for var in formula.variables if var.symbol in formula.formula_text]
        missing_vars = [var for var in required_vars if var not in inputs]
        
        if missing_vars:
            return {"error": f"필수 변수가 누락되었습니다: {missing_vars}"}
        
        # 소숫점 처리 검증
        validation_results = []
        for var_symbol, value in inputs.items():
            for var in formula.variables:
                if var.symbol == var_symbol and var.decimal_places is not None:
                    rounded_value = round(value, var.decimal_places)
                    if rounded_value != value:
                        validation_results.append(f"{var_symbol}: {value} -> {rounded_value} (소숫점 {var.decimal_places}자리)")
        
        return {
            "formula": formula,
            "inputs": inputs,
            "decimal_adjustments": validation_results,
            "status": "valid"
        }
    
    def export_formula_documentation(self, output_path: str) -> bool:
        """공식 문서화 출력"""
        try:
            documentation = {
                "title": "제주 시범사업 급전가능재생에너지자원 정산 공식",
                "source": "전력시장운영규칙 별표 33",
                "date_extracted": "2025-07-14",
                "formulas": {}
            }
            
            for formula_id, formula in self.formulas.items():
                documentation["formulas"][formula_id] = {
                    "name": formula.name,
                    "category": formula.category,
                    "resource_type": formula.resource_type,
                    "formula_text": formula.formula_text,
                    "variables": [
                        {
                            "symbol": var.symbol,
                            "name": var.name,
                            "unit": var.unit,
                            "description": var.description,
                            "decimal_places": var.decimal_places,
                            "constraints": var.constraints
                        } for var in formula.variables
                    ],
                    "calculation_steps": formula.calculation_steps,
                    "conditions": formula.conditions,
                    "decimal_handling": formula.decimal_handling
                }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(documentation, f, ensure_ascii=False, indent=2)
            
            logger.info(f"공식 문서화 완료: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"공식 문서화 실패: {e}")
            return False
    
    def get_calculation_example(self, formula_id: str) -> Dict[str, Any]:
        """공식 계산 예시"""
        formula = self.get_formula(formula_id)
        if not formula:
            return {"error": "공식을 찾을 수 없습니다"}
        
        if formula_id == "renewable_energy_settlement":
            return {
                "formula": formula.name,
                "example_inputs": {
                    "DA_SE i,t": 10.5,  # MW, 하루전에너지계획량
                    "DA_SMP t": 120.5,  # 원/kWh, 하루전에너지가격
                    "STLF i,t": 0.985,  # 손실계수
                    "MGO i,t": 10.8,    # MWh, 총 계량전력량
                    # 15분 구간별 데이터 (q=1~4)
                    "MGO i,t,1": 2.7,   # MWh, 01:00~01:15 계량전력량
                    "MGO i,t,2": 2.6,   # MWh, 01:15~01:30 계량전력량  
                    "MGO i,t,3": 2.8,   # MWh, 01:30~01:45 계량전력량
                    "MGO i,t,4": 2.7,   # MWh, 01:45~02:00 계량전력량
                    "RT_SMP t,1": 122.0, # 원/kWh, q=1 실시간에너지가격
                    "RT_SMP t,2": 125.0, # 원/kWh, q=2 실시간에너지가격
                    "RT_SMP t,3": 128.0, # 원/kWh, q=3 실시간에너지가격
                    "RT_SMP t,4": 124.0  # 원/kWh, q=4 실시간에너지가격
                },
                "calculation_steps": [
                    "1. DA_MP i,t = 120.5 × 0.985 = 118.69 원/kWh",
                    "2. DA_MEP i,t = 118.69 × 10.5 × 1 × 1,000 = 1,246,245 원",
                    "3. 15분 구간별 TPR_E 계산:",
                    "   TPR_E i,t,1 = 2.7/10.8 = 0.250, TPR_E i,t,2 = 2.6/10.8 = 0.241",
                    "   TPR_E i,t,3 = 2.8/10.8 = 0.259, TPR_E i,t,4 = 2.7/10.8 = 0.250",
                    "   검증: 0.250 + 0.241 + 0.259 + 0.250 = 1.000 ✓",
                    "4. 15분 구간별 실시간 거래가격:",
                    "   RT_MP i,t,1 = 122.0 × 0.985 = 120.17 원/kWh",
                    "   RT_MP i,t,2 = 125.0 × 0.985 = 123.13 원/kWh", 
                    "   RT_MP i,t,3 = 128.0 × 0.985 = 126.08 원/kWh",
                    "   RT_MP i,t,4 = 124.0 × 0.985 = 122.14 원/kWh",
                    "5. 15분 구간별 실시간 정산금 (편차 0.3MWh 배분):",
                    "   RT_MEP i,t,1 = 120.17 × 0.3 × 0.250 × 1,000 = 9,013 원",
                    "   RT_MEP i,t,2 = 123.13 × 0.3 × 0.241 × 1,000 = 8,903 원",
                    "   RT_MEP i,t,3 = 126.08 × 0.3 × 0.259 × 1,000 = 9,798 원", 
                    "   RT_MEP i,t,4 = 122.14 × 0.3 × 0.250 × 1,000 = 9,161 원",
                    "6. 총 실시간정산금 = 9,013 + 8,903 + 9,798 + 9,161 = 36,875 원",
                    "7. MEPi,t = 1,246,245 + 36,875 = 1,283,120 원"
                ],
                "decimal_handling": "계량전력량: 소숫점 셋째자리, 가격: 소숫점 둘째자리, TPR_E 소숫점 셋째자리"
            }
        
        elif formula_id == "aggregated_energy_settlement":
            return {
                "formula": formula.name,
                "example_inputs": {
                    "DA_SE i,t": 5.2,   # MW, 하루전에너지계획량 (입찰대상)
                    "MGO i,t": 5.8,     # MWh, 총 계량전력량
                    "DA_SMP t": 115.8,  # 원/kWh, 하루전에너지가격
                    "STLF i,t": 0.982,  # 손실계수
                    # 15분 구간별 데이터 (q=1~4)
                    "MGO i,t,1": 1.5,   # MWh, 01:00~01:15 계량전력량
                    "MGO i,t,2": 1.4,   # MWh, 01:15~01:30 계량전력량  
                    "MGO i,t,3": 1.6,   # MWh, 01:30~01:45 계량전력량
                    "MGO i,t,4": 1.3,   # MWh, 01:45~02:00 계량전력량
                    "RT_SMP t,1": 115.0, # 원/kWh, q=1 실시간에너지가격
                    "RT_SMP t,2": 118.0, # 원/kWh, q=2 실시간에너지가격
                    "RT_SMP t,3": 120.0, # 원/kWh, q=3 실시간에너지가격
                    "RT_SMP t,4": 117.0  # 원/kWh, q=4 실시간에너지가격
                },
                "calculation_steps": [
                    "1. DA_MP i,t = 115.8 × 0.982 = 113.72 원/kWh",
                    "2. (입찰대상) DA_MEP i,t = 113.72 × 5.2 × 1 × 1,000 = 591,344 원",
                    "3. 15분 구간별 TPR_E 계산:",
                    "   TPR_E i,t,1 = 1.5/5.8 = 0.259, TPR_E i,t,2 = 1.4/5.8 = 0.241",
                    "   TPR_E i,t,3 = 1.6/5.8 = 0.276, TPR_E i,t,4 = 1.3/5.8 = 0.224",
                    "   검증: 0.259 + 0.241 + 0.276 + 0.224 = 1.000 ✓",
                    "4. 15분 구간별 실시간 거래가격:",
                    "   RT_MP i,t,1 = 115.0 × 0.982 = 112.93 원/kWh",
                    "   RT_MP i,t,2 = 118.0 × 0.982 = 115.88 원/kWh", 
                    "   RT_MP i,t,3 = 120.0 × 0.982 = 117.84 원/kWh",
                    "   RT_MP i,t,4 = 117.0 × 0.982 = 114.89 원/kWh",
                    "5. 15분 구간별 실시간 정산금 (편차 0.6MWh 배분):",
                    "   RT_MEP i,t,1 = 112.93 × 0.6 × 0.259 × 1,000 = 17,563 원",
                    "   RT_MEP i,t,2 = 115.88 × 0.6 × 0.241 × 1,000 = 16,756 원",
                    "   RT_MEP i,t,3 = 117.84 × 0.6 × 0.276 × 1,000 = 19,524 원", 
                    "   RT_MEP i,t,4 = 114.89 × 0.6 × 0.224 × 1,000 = 15,439 원",
                    "6. 총 실시간정산금 = 17,563 + 16,756 + 19,524 + 15,439 = 69,282 원",
                    "7. MEPi,t = 591,344 + 69,282 = 660,626 원",
                    "※ 비입찰대상인 경우: DA_MEP i,t = 113.72 × 5.8 × 1,000 = 659,576 원, RT_MEP = 0"
                ],
                "decimal_handling": "비중앙급전발전기: 정산금 원 단위, 가격 소숫점 둘째자리, TPR_E 소숫점 셋째자리"
            }
        
        elif formula_id == "renewable_variable_cost_settlement":
            return {
                "formula": formula.name,
                "example_inputs": {
                    "SCMWG i,t": 1500000,    # 원, 변동비
                    "MPMWG i,t": 1200000,    # 원, 에너지정산금
                    "SCMWG_FLAG i,t": 1      # 지급플래그
                },
                "calculation_steps": [
                    "1. 변동비보전정산금 = Max(1,500,000 - 1,200,000, 0) × 1",
                    "2. MWP i,t = Max(300,000, 0) × 1 = 300,000 원"
                ],
                "decimal_handling": "변동비와 정산금: 원 단위"
            }
        
        return {"message": f"{formula.name}에 대한 계산 예시 준비 중"}


def main():
    """테스트 실행"""
    extractor = ActualFormulaExtractor()
    
    print("=== 제주 시범사업 급전가능재생에너지자원 정산 공식 ===")
    print(f"총 {len(extractor.formulas)}개 공식 로드됨\n")
    
    # 1. 모든 공식 나열
    for formula_id, formula in extractor.formulas.items():
        print(f"[{formula.category}] {formula.name}")
        print(f"공식: {formula.formula_text}")
        print(f"변수 수: {len(formula.variables)}개")
        print("-" * 50)
    
    # 2. 에너지정산금 공식 상세 정보
    energy_formula = extractor.get_formula("renewable_energy_settlement")
    if energy_formula:
        print(f"\n=== {energy_formula.name} 상세 정보 ===")
        print(f"공식: {energy_formula.formula_text}")
        print("\n변수 정의:")
        for var in energy_formula.variables:
            print(f"  {var.symbol}: {var.name} ({var.unit}) - {var.description}")
        
        print("\n계산 단계:")
        for step in energy_formula.calculation_steps:
            print(f"  {step}")
        
        print("\n조건:")
        for condition in energy_formula.conditions:
            print(f"  - {condition}")
    
    # 3. 계산 예시
    example = extractor.get_calculation_example("renewable_energy_settlement")
    if "calculation_steps" in example:
        print(f"\n=== 계산 예시 ===")
        for step in example["calculation_steps"]:
            print(f"  {step}")
    
    # 4. 문서화 출력
    doc_path = "jeju_renewable_settlement_formulas.json"
    if extractor.export_formula_documentation(doc_path):
        print(f"\n공식 문서화 완료: {doc_path}")


if __name__ == "__main__":
    main()