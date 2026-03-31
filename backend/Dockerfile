# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY app ./app
COPY run.py ./run.py

EXPOSE 8080

ENTRYPOINT ["uv", "run", "python", "run.py"]
