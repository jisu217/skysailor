FROM node:22-bookworm-slim AS frontend
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/src ./src
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY clover.py leaf.py dome.py rail.py b_control.py rail_strategy.py hanging.py rail_env.py training_dashboard.py benchmark.py agent_sandbox.py dashboard.py cap_drop.py ./
COPY participant-kit.zip ./
COPY participant/python-example ./participant/python-example
COPY participant/direct-example ./participant/direct-example
COPY participant/hanging-example ./participant/hanging-example
COPY data/wind/measured.json ./data/wind/
COPY web/src/cap/loads.json web/src/cap/rotation_damping.json ./web/src/cap/
COPY --from=frontend /web/dist ./web/dist
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=15s CMD /app/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["/app/.venv/bin/uvicorn", "dashboard:app", "--host", "0.0.0.0", "--port", "8000"]
