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

- `dags/apod_etl_dag.py` defines five tasks: extract → transform → load → dvc track → git commit/push
- Data is appended to `data/apod_data.csv` and upserted into Postgres table `apod`.
- DVC is initialized and `data/apod_data.csv` is tracked creating `data/apod_data.csv.dvc`.
- If `GIT_REMOTE_URL` is defined, changes are pushed to GitHub as part of the DAG.

## Switching to Astronomer Runtime

The Dockerfile uses the official Airflow base image for broad compatibility. To use Astronomer Runtime, change the base image line in `Dockerfile` to something like:

```
# FROM quay.io/astronomer/astro-runtime:<version>
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
