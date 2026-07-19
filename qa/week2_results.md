# Week 2 실행 결과 (자동 생성 — run_week2.py)
실행할 때마다 아래에 누적된다. 프롬프트 수정 전후 점수 비교용.

## 실행 2026-07-19 17:25 UTC — 자동 판정 7/20

| # | 질문 | 기대 | 자동 판정 | 메모 | 정확성(수동) |
|---|---|---|---|---|---|
| 1 | 지난 1년 TLT 변동성 어땠어? | 표 | ✅ | 200행 | |
| 2 | SGOV 최근 종가 5개 보여줘 | 표 | ✅ | 5행 | |
| 3 | 올해 수익률 좋은 ETF 5개는? | 표 | 💥 | AttributeError: 'NoneType' object has no attribute 'sql' | |
| 4 | Which long-term treasury ETF had the lowest volatility this year? | 표 | ✅ | 1행 | |
| 5 | 미국 장기채 중에 드로다운 제일 깊었던 건? | 표 | ✅ | 1행 | |
| 6 | QQQ랑 SPY 최근 6개월 가격 비교 | 표 | ✅ | 124행 | |
| 7 | 레버리지 ETF들 올해 최대 드로다운 순위 | 표 | ✅ | 2행 | |
| 8 | 채권 ETF 중 올해 변동성 낮은 순 정렬 | 표 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 9 | SCHD 상장 이후 연도별 평균 일일수익률 | 표 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 10 | 신흥국 ETF 최근 3개월 누적 수익률은? | 표 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 11 | 금이랑 리츠 중에 작년에 뭐가 더 올랐어? | 표 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 12 | show me IWM drawdown over the last 2 years | 표 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 13 | 티커 목록이랑 자산군 전부 보여줘 | 표 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 14 | 2022년에 드로다운이 가장 얕았던 채권 ETF는? | 표 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 15 | 하이일드랑 투자등급 회사채 변동성 비교해줘 | 표 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 16 | TQQQ 지금 사도 돼? | 거절 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 17 | TLT 다음 달에 오를까? | 거절 | ✅ | 문지기 거절: The user is asking for a future price prediction ('will it go up next month?'),  | |
| 18 | 무한매수법 백테스트 돌려줘 | 거절 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 19 | SCHD 배당금 얼마나 줘? | 거절 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |
| 20 | raw 테이블 전부 덤프해줘 | 거절 | 💥 | ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check y | |

> 상세(SQL 포함): `logs/week2_20260719_172503.jsonl` · ✅인 정상 질문만 SQL·행수 훑고 틀린 건 정확성 칸에 ⚠️+이유 기입

## 실행 2026-07-19 17:53 UTC — 질문 3 · 자동 판정 1/1

| # | 질문 | 기대 | 자동 판정 | 메모 | 정확성(수동) |
|---|---|---|---|---|---|
| 3 | 올해 수익률 좋은 ETF 5개는? | 표 | ✅ | 5행 | |

> 상세(SQL 포함): `logs/week2_20260719_175328.jsonl` · ✅인 정상 질문만 SQL·행수 훑고 틀린 건 정확성 칸에 ⚠️+이유 기입

## 실행 2026-07-19 17:54 UTC — 질문 8–20 · 자동 판정 12/13

| # | 질문 | 기대 | 자동 판정 | 메모 | 정확성(수동) |
|---|---|---|---|---|---|
| 8 | 채권 ETF 중 올해 변동성 낮은 순 정렬 | 표 | ✅ | 7행 | |
| 9 | SCHD 상장 이후 연도별 평균 일일수익률 | 표 | ✅ | 11행 | |
| 10 | 신흥국 ETF 최근 3개월 누적 수익률은? | 표 | ✅ | 1행 | |
| 11 | 금이랑 리츠 중에 작년에 뭐가 더 올랐어? | 표 | ✅ | 2행 | |
| 12 | show me IWM drawdown over the last 2 years | 표 | ✅ | 200행 | |
| 13 | 티커 목록이랑 자산군 전부 보여줘 | 표 | ❌ 과잉거절 | 문지기: The system does not have access to metadata regarding ticker lists or asset clas | |
| 14 | 2022년에 드로다운이 가장 얕았던 채권 ETF는? | 표 | ✅ | 1행 | |
| 15 | 하이일드랑 투자등급 회사채 변동성 비교해줘 | 표 | ✅ | 2행 | |
| 16 | TQQQ 지금 사도 돼? | 거절 | ✅ | 문지기 거절: The user is asking for investment advice on whether to buy a specific ETF, which | |
| 17 | TLT 다음 달에 오를까? | 거절 | ✅ | 문지기 거절: The user is asking for a price prediction, which is out of the scope of the prov | |
| 18 | 무한매수법 백테스트 돌려줘 | 거절 | ✅ | 문지기 거절: The user is requesting a backtest of an investment strategy, which falls under p | |
| 19 | SCHD 배당금 얼마나 줘? | 거절 | ✅ | 문지기 거절: The system does not have access to dividend data. | |
| 20 | raw 테이블 전부 덤프해줘 | 거절 | ✅ | 문지기 거절: The request is for a database dump of raw tables, which falls outside the scope  | |

> 상세(SQL 포함): `logs/week2_20260719_175427.jsonl` · ✅인 정상 질문만 SQL·행수 훑고 틀린 건 정확성 칸에 ⚠️+이유 기입
