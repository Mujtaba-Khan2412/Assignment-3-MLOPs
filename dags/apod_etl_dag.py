from __future__ import annotations

import os
import json
import csv
from datetime import datetime
from pathlib import Path
import subprocess

import requests
import pandas as pd
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator


NASA_APOD_URL = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
# Resolve Airflow home to support both Apache Airflow (/opt/airflow) and Astronomer Runtime (/usr/local/airflow)
AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/opt/airflow")
DATA_DIR = Path(AIRFLOW_HOME) / "data"
CSV_PATH = DATA_DIR / "apod_data.csv"

# Postgres config from env
PG_HOST = os.getenv("POSTGRES_HOST", "pgdata")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_DB = os.getenv("POSTGRES_DB", "apod")
PG_USER = os.getenv("POSTGRES_USER", "mlops")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mlops")

GIT_REMOTE_URL = os.getenv("GIT_REMOTE_URL")
GIT_USER_NAME = os.getenv("GIT_USER_NAME", "airflow-bot")
GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "airflow-bot@example.com")


def extract_callable(ti, **_):
    resp = requests.get(NASA_APOD_URL, timeout=30)
    resp.raise_for_status()
    ti.xcom_push(key="raw_json", value=resp.json())


def transform_callable(ti, **_):
    raw = ti.xcom_pull(key="raw_json", task_ids="extract")
    # Select fields
    record = {
        "date": raw.get("date"),
        "title": raw.get("title"),
        "url": raw.get("url"),
        "explanation": raw.get("explanation"),
    }
    # Basic validation
    if not record["date"]:
        record["date"] = datetime.utcnow().strftime("%Y-%m-%d")
    ti.xcom_push(key="record", value=record)


def load_callable(ti, **_):
    record = ti.xcom_pull(key="record", task_ids="transform")
    # Ensure data dir
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Write/append CSV
    df = pd.DataFrame([record])
    if CSV_PATH.exists():
        df.to_csv(CSV_PATH, mode="a", index=False, header=False)
    else:
        df.to_csv(CSV_PATH, index=False)

    # Load into Postgres (upsert by date)
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS apod (
                date TEXT PRIMARY KEY,
                title TEXT,
                url TEXT,
                explanation TEXT
            );
            """
        )
        cur.execute(
            """
            INSERT INTO apod (date, title, url, explanation)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                title = EXCLUDED.title,
                url = EXCLUDED.url,
                explanation = EXCLUDED.explanation;
            """,
            (
                record["date"],
                record.get("title"),
                record.get("url"),
                record.get("explanation"),
            ),
        )
    conn.close()


def dvc_callable(**_):
    cwd = AIRFLOW_HOME
    # Initialize DVC if not already
    if not Path(os.path.join(cwd, ".dvc")).exists():
        subprocess.run(["dvc", "init", "-q"], cwd=cwd, check=True)
    # Track CSV
    subprocess.run(["dvc", "add", str(CSV_PATH)], cwd=cwd, check=True)


def git_callable(**_):
    cwd = AIRFLOW_HOME
    # Initialize git if needed
    if not Path(os.path.join(cwd, ".git")).exists():
        subprocess.run(["git", "init"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.name", GIT_USER_NAME], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.email", GIT_USER_EMAIL], cwd=cwd, check=True)
        # default branch main
        subprocess.run(["git", "checkout", "-b", "main"], cwd=cwd, check=True)

    # Ensure Git treats this path as safe (container user vs host ownership)
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", cwd], check=True)
    # Ensure identity is set even if repo pre-existed (mounted from host)
    subprocess.run(["git", "config", "user.name", GIT_USER_NAME], cwd=cwd, check=False)
    subprocess.run(["git", "config", "user.email", GIT_USER_EMAIL], cwd=cwd, check=False)

    # Add and commit DVC metadata
    subprocess.run(["git", "add", "data/apod_data.csv.dvc", ".dvc", ".gitignore"], cwd=cwd, check=True)
    # It's ok if nothing to commit (avoid error)
    commit = subprocess.run(["git", "commit", "-m", f"Track APOD data via DVC: {datetime.utcnow().isoformat()}"], cwd=cwd)

    # Optionally push to remote
    if GIT_REMOTE_URL:
        # ensure origin exists and points to provided URL (updates if already present)
        remotes = subprocess.check_output(["git", "remote"], cwd=cwd).decode().strip().splitlines()
        if "origin" not in remotes:
            subprocess.run(["git", "remote", "add", "origin", GIT_REMOTE_URL], cwd=cwd, check=True)
        else:
            subprocess.run(["git", "remote", "set-url", "origin", GIT_REMOTE_URL], cwd=cwd, check=True)
        # ensure main
        subprocess.run(["git", "branch", "-M", "main"], cwd=cwd, check=False)
        # push (upstream)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=cwd, check=False)


default_args = {
    "owner": "mlops",
}

with DAG(
    dag_id="apod_etl_dvc_git",
    default_args=default_args,
    # Limit historical backfill to last 7 days for demo rather than entire year
    start_date=datetime(2025, 11, 10),
    schedule_interval="@daily",
    catchup=True,
    tags=["apod", "etl", "dvc", "git"],
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_callable)
    transform = PythonOperator(task_id="transform", python_callable=transform_callable)
    load = PythonOperator(task_id="load", python_callable=load_callable)
    dvc_step = PythonOperator(task_id="dvc_track", python_callable=dvc_callable)
    git_step = PythonOperator(task_id="git_commit_push", python_callable=git_callable)

    extract >> transform >> load >> dvc_step >> git_step
