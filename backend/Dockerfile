# Build context = repo root:  docker build -f backend/Dockerfile -t nightlife-backend .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    DATABASE_URL=sqlite:////app/var/app.db \
    LIVE_SIM_DB=/app/data/live_sim.db \
    ALLOW_FIXTURE_SIM=0

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt "psycopg[binary]==3.2.*"

# Public data (read-only) + optional repo packages; missing ones are fine (see build_sim.sh).
COPY data/ data/
COPY backend/ backend/
COPY . /tmp/repo
RUN for d in simulator recs; do [ -d /tmp/repo/$d ] && cp -r /tmp/repo/$d /app/$d || true; done \
 && rm -rf /tmp/repo

# live_sim.db is generated at BUILD time (v2 §J), never at boot.
RUN bash backend/scripts/build_sim.sh

RUN useradd --create-home --uid 10001 app && mkdir -p /app/var && chown -R app /app/var
USER app
ENV PYTHONPATH=/app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health')"
CMD ["bash", "backend/scripts/start.sh"]
