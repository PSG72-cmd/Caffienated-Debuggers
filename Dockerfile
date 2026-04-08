FROM python:3.12-slim

WORKDIR /app/env
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md openenv.yaml ./
COPY ticket_triage_env ./ticket_triage_env
COPY inference.py ./inference.py
COPY app.py ./app.py

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

ENV PYTHONPATH=/app/env
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health')" || exit 1

CMD ["uvicorn", "ticket_triage_env.server.app:app", "--host", "0.0.0.0", "--port", "7860"]
