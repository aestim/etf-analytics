"""
Week 1 exercise: Gemini structured output — question intent classifier.

Run:   python qa/practice_structured.py
Pass:  all questions parse into the pydantic schema, and the advice/backtest
       ones are classified out_of_scope.

This classifier became stage 1 of the Week 2 text-to-SQL pipeline (ask.py).
"""

import os
from typing import Literal

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

load_dotenv()


# --- 1. Response schema ---------------------------------------------------
class QuestionIntent(BaseModel):
    intent: Literal["data_query", "out_of_scope"]
    tickers: list[str]        # tickers mentioned in the question (empty if none)
    metric: Literal["price", "return", "volatility", "drawdown", "unknown"]
    reason: str               # one-sentence justification


# --- 2. Allowed scope as the system prompt --------------------------------
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
    "지난 1년 TLT 변동성 어땠어?",   # KR "TLT volatility, past year" — expect: data_query
    "TQQQ 지금 사도 돼?",            # KR "should I buy TQQQ?" — expect: out_of_scope
    "무한매수법 백테스트 해줘",       # KR "backtest infinite buying" — expect: out_of_scope
    "Which ETF had the lowest volatility this year",  # expect: data_query
]


def classify(question: str, model: str | None = None):
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
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
