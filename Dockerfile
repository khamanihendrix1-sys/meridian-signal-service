FROM python:3.12-slim as builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN python -m pip install --upgrade pip poetry==1.8.3
RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-root --sync

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . /app
RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
ENV PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
CMD ["uvicorn", "meridian.main:app", "--host", "0.0.0.0", "--port", "8000"]
