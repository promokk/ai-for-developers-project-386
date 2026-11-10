FROM node:26.13.0-bookworm-slim AS frontend-build
WORKDIR /app
RUN npm install --global pnpm@12.18.0
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY contracts/package.json contracts/
COPY frontend/package.json frontend/
RUN pnpm install --frozen-lockfile
COPY frontend frontend
RUN pnpm --dir frontend exec vite build

FROM python:3.13.18-slim-bookworm AS backend-build
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.13.18-slim-bookworm AS runtime
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
ENV PATH="/app/backend/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    CALENDAR_STATIC_DIR=/app/static
WORKDIR /app
COPY --from=backend-build /app/backend/.venv /app/backend/.venv
COPY --from=frontend-build /app/frontend/dist /app/static
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health', timeout=2)"]
CMD ["sh", "-c", "exec uvicorn calendar_api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
