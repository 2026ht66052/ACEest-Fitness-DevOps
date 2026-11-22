# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# ACEest Fitness & Gym — production image
# Multi-stage build: dependencies are compiled into a wheel layer, then copied
# into a slim runtime image that runs as an unprivileged user.
# Build:  docker build --build-arg APP_VERSION=3.2.4 -t <user>/aceest-fitness:3.2.4 .
# ---------------------------------------------------------------------------

# ----------------------------- build stage ---------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---------------------------- runtime stage --------------------------------
FROM python:3.12-slim AS runtime

ARG APP_VERSION=3.2.4
ARG APP_TRACK=stable
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="ACEest Fitness & Gym" \
      org.opencontainers.image.description="Flask gym management service" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION} \
    APP_TRACK=${APP_TRACK} \
    DATABASE_PATH=/data/aceest_fitness.db \
    PORT=5000

WORKDIR /app

# Install dependencies from the pre-built wheels (no compiler in the final image)
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Application code
COPY app/ ./app/
COPY wsgi.py gunicorn.conf.py ./

# Unprivileged runtime user and a writable volume for the SQLite database
RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 aceest \
    && mkdir -p /data \
    && chown -R aceest:aceest /app /data
USER aceest
VOLUME ["/data"]

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2).status==200 else 1)"

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
