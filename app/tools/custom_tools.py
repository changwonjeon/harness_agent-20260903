"""
app/tools/custom_tools.py

🎯 Mission 01: 나만의 커스텀 도구(Custom Tool) 작성하기
missions/01_mission_add_custom_tool.md 가이드를 참고하여, 
LangChain의 @tool 데코레이터를 이용해 에이전트가 호출할 수 있는 도구 함수를 작성하세요.

[핵심 팁]
1. @tool(parse_docstring=True)를 적용합니다.
2. Docstring의 첫 줄에는 도구의 목적을 명확히 작성합니다.
3. 언제 이 도구를 호출해야 하는지 '트리거 조건(호출 규칙)'을 반드시 Docstring에 명시합니다.
4. Args: 섹션에 각 파라미터의 타입과 설명을 작성합니다.
"""

import json
import math
import random
import re

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool


# -------------------------------------------------------------------------------
# TODO: 나만의 커스텀 도구를 아래에 작성하세요.
# 예시 1) 주사위 굴리기 (roll_dice)
# 예시 2) 환율 계산기 (convert_currency)
# 예시 3) 로또 번호 추천, 가상 코인 던지기, 간단 메모 등 자유롭게 작성 가능!
# -------------------------------------------------------------------------------

# @tool(parse_docstring=True)
# def my_custom_tool(param: str) -> str:
#     """도구에 대한 설명문 및 호출 조건을 작성하세요.
    
#     Args:
#         param: 파라미터 설명
#     """
#     return "도구 실행 결과"

@tool(parse_docstring=True)
def roll_dice(num_dices: int = 1, num_sides: int = 6) -> str:
    """주사위를 굴리는 도구입니다. 주사위를 굴려야 할 때 호출하세요. 1개 주사위의 면의 숫자는 num_sides으로, 주사위 갯수는 num_dices로 설정할 수 있습니다. 

    Args:
        num_dices: 굴릴 주사위의 개수 (기본값: 1, 최대값: 100, 0보다 큰 int)
        num_sides: 주사위의 면 수 (기본값: 6, 최소값: 2, 최대값: 20, 0보다 큰 int)

    Returns:
        주사위 결과를 문자열로 반환
    """
    results = [random.randint(1, num_sides) for _ in range(num_dices)]
    return f"주사위 결과: {results}, 주사위 눈금 합산: {sum(results)}"


@tool(parse_docstring=True)
def convert_currency(
    amount: float,
    from_currency: str = "USD",
    to_currency: str = "KRW",
) -> str:
    """네이버의 현재 기준환율로 USD, JPY, CNY, EUR, KRW 간 금액을 환산합니다.

    사용자가 달러, 엔화, 중국 위안화, 유로화, 원화의 현재 환율이나 환전 금액을 물으면 반드시 호출하세요.

    Args:
        amount: 환산할 기준 금액 (0보다 큰 숫자)
        from_currency: 사용자가 보유한 기준 통화 코드 또는 이름 (USD, JPY, CNY, EUR, KRW)
        to_currency: 바꾸려는 대상 통화 코드 또는 이름 (USD, JPY, CNY, EUR, KRW)

    Returns:
        환산 결과와 계산에 사용한 네이버 기준환율
    """
    aliases = {
        "USD": "USD", "달러": "USD", "미국달러": "USD",
        "JPY": "JPY", "엔": "JPY", "엔화": "JPY", "일본엔": "JPY",
        "CNY": "CNY", "위안": "CNY", "위안화": "CNY", "중국위안화": "CNY",
        "EUR": "EUR", "유로": "EUR", "유로화": "EUR",
        "KRW": "KRW", "원": "KRW", "원화": "KRW", "한국원": "KRW",
    }
    source = aliases.get(str(from_currency).strip().upper())
    target = aliases.get(str(to_currency).strip().upper())
    supported = "USD(달러), JPY(엔화), CNY(중국 위안화), EUR(유로화), KRW(원화)"

    if source is None or target is None:
        return f"⚠️ 지원하지 않는 통화입니다. 지원 통화: {supported}"

    try:
        numeric_amount = float(amount)
    except (TypeError, ValueError):
        return "⚠️ 금액은 숫자로 입력해 주세요."
    if not math.isfinite(numeric_amount) or numeric_amount <= 0:
        return "⚠️ 금액은 0보다 큰 유한한 숫자여야 합니다."

    needed_codes = list(dict.fromkeys(code for code in (source, target) if code != "KRW"))
    try:
        quotes = {code: _fetch_naver_quote(code) for code in needed_codes}
    except (requests.RequestException, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return f"⚠️ 네이버 환율을 조회하지 못했습니다. 잠시 후 다시 시도해 주세요. ({exc})"

    source_rate = 1.0 if source == "KRW" else quotes[source]["krw_per_unit"]
    target_rate = 1.0 if target == "KRW" else quotes[target]["krw_per_unit"]
    converted = numeric_amount * source_rate / target_rate

    rate_lines = []
    for code in needed_codes:
        quote = quotes[code]
        rate_lines.append(
            f"- {quote['basis_amount']:g} {code} = {quote['display_rate']:,.2f} KRW "
            f"({quote['traded_at']}, 하나은행 고시)"
        )
    if not rate_lines:
        rate_lines.append("- 1 KRW = 1 KRW")

    return (
        f"💱 네이버 환율 환산: {numeric_amount:,.2f} {source} = {converted:,.2f} {target}\n"
        "📌 적용 기준환율\n"
        + "\n".join(rate_lines)
        + "\n🔗 출처: 네이버페이 증권 환율"
    )


def _fetch_naver_quote(currency: str) -> dict:
    """네이버페이 증권 페이지에서 외화의 KRW 기준환율을 읽습니다."""
    url = f"https://m.stock.naver.com/marketindex/exchange/FX_{currency}KRW"
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    response.raise_for_status()

    script = BeautifulSoup(response.text, "html.parser").find("script", id="__NEXT_DATA__")
    if script is None or not script.string:
        raise ValueError("환율 데이터 영역을 찾을 수 없습니다")

    payload = json.loads(script.string)
    quote = _find_naver_quote(payload, f"FX_{currency}KRW")
    display_rate = float(str(quote["calcPrice"]).replace(",", ""))
    basis_amount = 100.0 if currency == "JPY" else 1.0
    return {
        "display_rate": display_rate,
        "basis_amount": basis_amount,
        "krw_per_unit": display_rate / basis_amount,
        "traded_at": quote["localTradedAt"],
    }


def _find_naver_quote(value, reuters_code: str) -> dict:
    """중첩된 네이버 페이지 데이터에서 실제 환율 시세 객체를 찾습니다."""
    if isinstance(value, dict):
        if value.get("reutersCode") == reuters_code and value.get("calcPrice"):
            return value
        for child in value.values():
            try:
                return _find_naver_quote(child, reuters_code)
            except ValueError:
                continue
    elif isinstance(value, list):
        for child in value:
            try:
                return _find_naver_quote(child, reuters_code)
            except ValueError:
                continue
    raise ValueError(f"{reuters_code} 환율 시세를 찾을 수 없습니다")


@tool(parse_docstring=True)
def memo_writer(param: str) -> str:
    """사용자가 나열한 텍스트를 세 개의 불릿씩 묶어 읽기 좋은 메모로 정리합니다.

    사용자가 여러 내용을 메모, 요약, 불릿 목록으로 정리해 달라고 하면 반드시 호출하세요.

    Args:
        param: 줄바꿈, 쉼표, 세미콜론 또는 문장으로 나열한 메모 내용

    Returns:
        불릿 세 줄마다 빈 줄로 구분한 메모 요약
    """
    if not isinstance(param, str) or not param.strip():
        return "⚠️ 정리할 메모 내용을 입력해 주세요."

    raw_items = re.split(r"(?:\r?\n)+|[,;；]+|(?<=[.!?。！？])\s+", param.strip())
    items = []
    for raw_item in raw_items:
        item = re.sub(r"^\s*(?:[-*•]+|\d+[.)])\s*", "", raw_item).strip()
        if item and item not in items:
            items.append(item)

    if not items:
        return "⚠️ 정리할 메모 내용을 입력해 주세요."

    blocks = []
    for start in range(0, len(items), 3):
        blocks.append("\n".join(f"• {item}" for item in items[start:start + 3]))
    return "📝 메모 요약\n\n" + "\n\n".join(blocks)
