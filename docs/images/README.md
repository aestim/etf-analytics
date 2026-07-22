# Screenshot capture guide

Save reviewed PNGs here and commit them. Selected current images are embedded in the main README.

| File | What to capture |
|------|-----------------|
| `dashboard-overview.png` | Streamlit home — default English view, language control, beginner guide and representative ETF charts |
| `ticker-guide.png` | Ticker guide expander — table + one detail card open |
| `strategy-lab.png` | Strategy Lab — equity curves + drawdown chart |
| `ask-example.png` | Ask — one Korean relationship question after switching the interface to 한국어, with conclusion, chart and table |
| `airflow-dag.png` | Airflow UI — `etf_pipeline` all tasks green |
| `dbt-test-success.png` | Terminal — `dbt test` all passing |

## How

```bash
cd ~/etf-analytics && docker compose up -d
source .venv/bin/activate
streamlit run dashboard/app.py     # http://localhost:8501  → Cmd+Shift+4 to capture
```

Airflow: http://localhost:8080 (admin/admin) → unpause `etf_pipeline` → Trigger → Graph view green → capture.

dbt: `cd dbt && dbt seed && dbt run && dbt test` → capture the green summary.

## Add to git

```bash
git add docs/images/*.png && git commit -m "docs: refresh demo screenshots" && git push
```
