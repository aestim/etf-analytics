FROM apache/airflow:2.9.1-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY ingest/requirements.txt /tmp/ingest-requirements.txt
RUN pip install --no-cache-dir -r /tmp/ingest-requirements.txt \
    && pip install --no-cache-dir "dbt-core>=1.7,<2" "dbt-postgres>=1.7,<2"
