FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY prompts ./prompts
COPY gpt ./gpt
RUN pip wheel --wheel-dir /wheels .

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BVR_EPHE_PATH=/app/ephe \
    PORT=8000

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY scripts ./scripts
RUN python scripts/fetch_ephemeris.py --output /app/ephe

EXPOSE 8000
CMD ["sh", "-c", "uvicorn bvr_star.api.app:app --host 0.0.0.0 --port ${PORT}"]
