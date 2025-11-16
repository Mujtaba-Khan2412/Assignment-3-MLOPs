# Custom Airflow image with required MLOps tooling
# Astronomer Runtime image (includes Airflow + production hardening)
# Reference versions: https://docs.astronomer.io/runtime/release-notes
# Choose a runtime matching Airflow 2.9.x
FROM quay.io/astronomer/astro-runtime:10.3.0

# Install system packages (git for code ops)
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Switch to Astronomer runtime user and install Python deps
USER astro
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Create standard project dirs under AIRFLOW_HOME used by Astronomer (/usr/local/airflow)
RUN mkdir -p /usr/local/airflow/dags /usr/local/airflow/data /usr/local/airflow/logs /usr/local/airflow/plugins /usr/local/airflow/include

# Default command runs Airflow in standalone (scheduler + webserver)
# Explicitly use tini (present in Astronomer Runtime) to supervise processes
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash", "-lc", "airflow db init && airflow webserver & airflow scheduler"]
