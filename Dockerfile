FROM ghcr.io/astral-sh/uv:python3.14-alpine AS builder
WORKDIR /srv

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY app/ ./app/
RUN uv sync --locked --no-dev

FROM python:3.14-alpine
WORKDIR /srv

COPY --from=builder /srv /srv
COPY alembic.ini .
ENV PATH="/srv/.venv/bin:$PATH"

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

