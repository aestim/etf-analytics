"""
Week 1 실습: Gemini structured output — 질문 의도 분류기.

실행:  python qa/practice_structured.py
합격:  질문 3개 모두 pydantic 파싱 성공 + 2·3번이 out_of_scope로 분류.

TODO를 위에서부터 채우면 됨. 이 분류기는 Week 2 text-to-SQL의 1단계가 된다.
"""

import os
from typing import Literal

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

load_dotenv()


# --- TODO 1: 응답 스키마 정의 -------------------------------------------
class QuestionIntent(BaseModel):
    intent: Literal["data_query", "out_of_scope"]
    tickers: list[str]        # 질문에 언급된 티커 (없으면 빈 리스트)
    metric: Literal["price", "return", "volatility", "drawdown", "unknown"]
    reason: str               # 분류 근거 한 문장


# --- TODO 2: 허용 범위를 시스템 프롬프트로 ------------------------------
SYSTEM_PROMPT = """
You are a gatekeeper for an ETF analytics Q&A system.
Classify the user's question. Questions may be in Korean or English.

data_query = can be answered from our warehouse: daily prices, returns,
volatility, drawdown per ETF — lookups, aggregations, rankings, comparisons.

out_of_scope = predictions ("will it go up?"), investment advice ("should I buy?"),
path-dependent simulations (backtests, DCA), or data we don't have
(dividends, fees, news, reasons why).

Extract any tickers mentioned. Pick the single most relevant metric.
Write `reason` as one short English sentence (the UI is English-only),
regardless of the question's language.
"""

QUESTIONS = [
    "지난 1년 TLT 변동성 어땠어?",   # 기대: data_query
    "TQQQ 지금 사도 돼?",            # 기대: out_of_scope
    "무한매수법 백테스트 해줘",       # 기대: out_of_scope
    "Which ETF had the lowest volatility this year", # 기대: data_query
]


def classify(question: str, model: str | None = None):
    # TODO 3: client = genai.Client(api_key=...)
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    # TODO 4:
    response = client.models.generate_content(
        model=model or os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
        contents=question,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "response_mime_type": "application/json",
            "response_schema": QuestionIntent,
        },
    )
    return response.parsed


if __name__ == "__main__":
    for q in QUESTIONS:
        result = classify(q)
        print(f"Q: {q}")
        print(f"   → {result}\n")
