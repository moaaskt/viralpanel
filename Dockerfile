FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

FROM base AS deps
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# Instalação do Playwright Chromium e dependências necessárias de sistema para headless scraping
RUN playwright install --with-deps chromium

FROM deps AS runtime
COPY . .
ENV PYTHONPATH=/app/src
