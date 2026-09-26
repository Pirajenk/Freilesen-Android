FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8765

WORKDIR /app

COPY server.py ./server.py
COPY preview/ ./preview/
COPY data/source_catalog.json ./data/source_catalog.json
COPY data/independent_sources.json ./data/independent_sources.json

RUN adduser --system --uid 10001 --no-create-home freilesen
USER 10001:10001

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8765/healthz', timeout=3)"

CMD ["python", "server.py"]
