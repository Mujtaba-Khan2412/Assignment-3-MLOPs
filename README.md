# APOD ETL with Airflow, DVC, and Postgres

This project builds a reproducible ETL pipeline that:

- Extracts NASA APOD daily JSON
- Transforms to selected fields (date, title, url, explanation)
- Loads into Postgres and appends to a CSV
- Tracks the CSV with DVC
- Commits the DVC metadata with Git (and optionally pushes to GitHub)

The Airflow image is prepared for deployment parity on platforms like Astronomer by using a custom Docker image with all required dependencies.

## Quick Start

Prerequisites:

- Docker Desktop (with WSL2 backend) installed and running
- Windows PowerShell terminal

### 1) Clone or open the project

```
cd e:\MLOPs\Assignment3
```

### 2) (Optional) Configure GitHub push from DAG

Create a `.env` at project root and set a tokenized remote URL. Example:

```
Copy-Item .env.example .env
# Edit .env and set GIT_REMOTE_URL like below
# GIT_REMOTE_URL=https://<TOKEN>@github.com/<user>/<repo>.git
```

Notes:

- Use a GitHub PAT with `repo` scope.
- The DAG will initialize git and push to `main`.

### 3) Build and start

```
docker compose build
docker compose up -d
```

Airflow UI: http://localhost:8080

The `airflow standalone` command creates an admin user automatically and prints credentials to logs. Get the password with:

```
docker logs apod_airflow --since 5m | Select-String -Pattern "username|password"
```

### 4) Trigger the DAG

Log in to the Airflow UI, unpause `apod_etl_dvc_git`, and trigger a run.

Alternatively from inside the container:

```
docker exec -it apod_airflow bash -lc "airflow dags list; airflow dags trigger apod_etl_dvc_git"
```

## How It Works

## Switching to Astronomer Runtime

## Astronomer Runtime

This project now uses an Astronomer Runtime base image (`quay.io/astronomer/astro-runtime:10.3.0`) for production parity. The container runs both scheduler and webserver processes. Rebuild anytime after changes:

```
docker compose build
docker compose up -d --force-recreate
```

## Daily Scheduling & Historical Runs

The DAG is scheduled `@daily` with `catchup=True` and a `start_date` set 7 days prior to current date to generate multiple historical runs for demo. After unpausing the DAG, Airflow scheduler will create a run for each missing day automatically.
To observe:

```
docker exec -it apod_airflow bash -lc "airflow dags list-runs -d apod_etl_dvc_git"
```

If you need a longer history (e.g., 30 days), change `start_date` in `dags/apod_etl_dag.py` and unpause again.

```

Then rebuild: `docker compose build`.

## Useful Commands

```

# Check services

docker compose ps

# Logs

docker logs -f apod_airflow

# PSQL into the Postgres (host port 5433)

# Requires psql on host or use the container

# docker exec -it apod_pg psql -U mlops -d apod

# List DAGs and trigger

docker exec -it apod_airflow bash -lc "airflow dags list"
docker exec -it apod_airflow bash -lc "airflow dags trigger apod_etl_dvc_git"

```

## Cleanup

```

docker compose down -v

```

```
