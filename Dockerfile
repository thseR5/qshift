FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 QSHIFT_OUTPUT_DIR=/tmp/qshift-output
WORKDIR /app
RUN adduser --system --group --no-create-home qshift
COPY pyproject.toml alembic.ini ./
COPY qshift ./qshift
COPY alembic ./alembic
RUN pip install --no-cache-dir .
USER qshift
