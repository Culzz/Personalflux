FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

# Run as a non-root user: a compromised process should not own the app directory.
RUN useradd --create-home --uid 10001 app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini alembic.ini
COPY alembic alembic
COPY app app

# The artefact directory is writable by the app user. A deployment without a
# mounted disk fills it from MODEL_ARTIFACT_URL on boot; a local build can copy a
# trained version in beforehand. A clone without artefacts still builds, because
# the folder always exists (it holds a placeholder file).
COPY model_artifacts /artifacts
ENV MODEL_ARTIFACT_DIR=/artifacts
RUN mkdir -p /artifacts && chown -R app:app /code /artifacts
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD python -c "import os,urllib.request,sys;p=os.environ.get('PORT','8000');sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+p+'/health',timeout=4).status==200 else 1)"

# Migrations run once per container start. Several workers load the model, and
# each one adopts a promotion on its own poll, which is why more than one is safe.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips '*' --timeout-keep-alive 5 --limit-concurrency 256"]
