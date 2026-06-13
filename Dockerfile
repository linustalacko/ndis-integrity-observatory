# Single-service image: build the SvelteKit SPA, then serve it + the API from FastAPI.

# --- stage 1: build the frontend ---
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- stage 2: python runtime (match .python-version) ---
FROM python:3.11-slim
WORKDIR /app

# uv for fast, reproducible installs
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# app code + data (prebuilt DB, catalogue, synthetic batch)
COPY app/ ./app/
COPY api/ ./api/
COPY data/ ./data/
COPY --from=web /web/build ./frontend/build

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uv run uvicorn api.server:app --host 0.0.0.0 --port ${PORT}"]
