# Screenshot capture guide

Save PNGs here and commit. GitHub README embeds them automatically.

| File | What to capture |
|------|-----------------|
| `dashboard-volatility-snapshot.png` | Streamlit — vol chart + snapshot table |
| `dashboard-prices-returns.png` | Streamlit — adjusted close + cumulative return |
| `airflow-dag.png` | Airflow UI — DAG graph or successful run |
| `dbt-test-success.png` | Terminal — `dbt test` all green |

---

## 1. Dashboard (Streamlit)

```bash
cd ~/etf-analytics
docker compose up -d postgres
# ingest + dbt once if DB is empty (see main README)
cd dashboard && pip install -r requirements.txt && streamlit run app.py
```

Open http://localhost:8501 → **Cmd+Shift+4** (macOS) → drag to capture each half-screen.

---

## 2. Airflow

```bash
cd ~/etf-analytics && docker compose up -d
```

1. Open http://localhost:8080 → login `admin` / `admin`
2. Find DAG **`etf_pipeline`** → toggle **Unpause**
3. **Trigger DAG** (play button) and wait until all tasks are green
4. Open **Graph** or **Grid** view showing success → screenshot → save as `airflow-dag.png`

Good shots: DAG list with `etf_pipeline` enabled, or Graph view with three green tasks.

---

## 3. dbt test (terminal)

```bash
cd ~/etf-analytics
docker compose up -d postgres
export POSTGRES_HOST=localhost POSTGRES_PORT=5433
export POSTGRES_USER=etf POSTGRES_PASSWORD=etf POSTGRES_DB=etf_analytics

python3.10 -m venv .venv && source .venv/bin/activate
pip install "dbt-core>=1.7" "dbt-postgres>=1.7"
cd dbt && cp -n profiles.yml.example profiles.yml
../.venv/bin/dbt deps && ../.venv/bin/dbt run && ../.venv/bin/dbt test
```

Screenshot the terminal when you see **`Completed successfully`** and **`PASS=12`**.

Save as `dbt-test-success.png`.

---

## Add to git

```bash
cd ~/etf-analytics
git add docs/images/*.png README.md
git commit -m "Add Airflow and dbt demo screenshots"
git push
```
