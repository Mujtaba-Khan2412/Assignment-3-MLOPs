# Custom Airflow image with required MLOps tooling
FROM apache/airflow:2.9.3

# Install system packages (git for code ops)
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Switch back to airflow user and install Python deps
USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Create standard project dirs
RUN mkdir -p /opt/airflow/dags /opt/airflow/data /opt/airflow/logs /opt/airflow/plugins /opt/airflow/include

# Default command runs Airflow in standalone (scheduler + webserver)
CMD ["bash", "-lc", "airflow standalone"]
