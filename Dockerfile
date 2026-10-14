# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV APP_DATA_DIR=/data
ENV HF_HOME=/data/.cache/huggingface
ENV XDG_CACHE_HOME=/data/.cache
ENV OMP_NUM_THREADS=2
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

ARG VCS_REF=local
LABEL org.opencontainers.image.source="https://github.com/iaketo/ia-components-devops" \
      org.opencontainers.image.revision=$VCS_REF

WORKDIR /app

COPY requirements-docker.txt .

# Certificado/bundle público opcional para proxies corporativos, sin desactivar TLS.
RUN --mount=type=secret,id=cloud_ca,target=/tmp/cloud-ca.crt \
    if [ -s /tmp/cloud-ca.crt ]; then \
      cat /tmp/cloud-ca.crt >> /etc/ssl/certs/ca-certificates.crt; \
    fi \
    && python -m pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.14.1+cpu' \
    && pip install -r requirements-docker.txt \
    && pip check

COPY . .

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser \
    && chmod -R a+rX /app \
    && mkdir -p /data/memory /data/observability_data /data/.cache \
    && chown -R appuser:appuser /data /home/appuser

USER appuser

EXPOSE 8501

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=60s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)" || exit 1

CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
