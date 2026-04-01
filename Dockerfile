# syntax = docker/dockerfile:1.9-labs

# ────────────────────────────────────────────────
# Стадия 1 — сборка зависимостей (builder)
# ────────────────────────────────────────────────
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Устанавливаем системные зависимости для сборки Rust и Python пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Rust для сборки нативных расширений
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"

# Копируем только lock-файлы / requirements (самое важное!)
COPY pyproject.toml uv.lock requirements.txt* ./

# Устанавливаем uv и синхронизируем зависимости
RUN --mount=type=cache,target=/root/.cache/uv \
    pip install --no-cache-dir uv && \
    uv sync --frozen --no-install-project --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# ------------------- ЗАГРУЗКА МОДЕЛИ -------------------
# Здесь можно закомментированные команды для загрузки модели оставить
# RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('deepvk/USER-bge-m3')"

# ────────────────────────────────────────────────
# Стадия 2 — финальный образ (runtime)
# ────────────────────────────────────────────────
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Копируем виртуальное окружение из builder
COPY --from=builder /app/.venv /app/.venv

# Добавляем venv в PATH
ENV PATH="/app/.venv/bin:$PATH"

# Копируем весь код
COPY . .

# Если используете fastapi/uvicorn/gunicorn
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["python", "main.py"]
