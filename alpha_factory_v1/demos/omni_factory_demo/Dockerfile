# SPDX-License-Identifier: Apache-2.0
# ────────────────────────────────────────────────────────────────────────────────
#  OMNI-Factory • Smart-City Resilience Demo   (Alpha-Factory v1 👁️✨)
#  FINAL, COMPLETE, PRODUCTION-READY DOCKERFILE              – file #5 / 5
#
#  • Non-root, slim, SBOM-ready, reproducible build
#  • Runs the open-ended multi-agent core + Prometheus exporter + Dash dashboard
#  • Zero configuration required; works online (OpenAI key) or offline
#
#  Usage:
#     docker build  --tag omni-factory:latest .
#     docker run -p 8050:8050 -p 9137:9137 \
#                -e OPENAI_API_KEY=$OPENAI_API_KEY \
#                omni-factory:latest
# ────────────────────────────────────────────────────────────────────────────────

############################
# 1️⃣  Build stage (light) #
############################
FROM python:3.11.13-slim as base

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.title="OMNI-Factory Demo" \
      org.opencontainers.image.description="Self-contained, open-ended smart-city simulation with live dashboard and metrics." \
      org.opencontainers.image.licenses="Apache-2.0" \
      maintainer="Alpha-Factory Engineering <ops@alpha-factory.ai>"

############################
# 2️⃣  Dependencies stage  #
############################
FROM base as deps

# System packages ──────────────────────────────────────────────────────────────
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        build-essential  \
        curl \
        git \
        libgl1 \
        && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies ──────────────────────────────────────────────────────────
#  • Pinned for deterministic builds.
#  • Using --require-hashes to guarantee integrity (hashes generated via pip-tools).
COPY ./alpha_factory_v1/demos/omni_factory_demo/requirements.lock /tmp/requirements.lock
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock

############################
# 3️⃣  Runtime   stage     #
############################
FROM base as runtime

# Copy virtualenv from deps stage
COPY --from=deps /usr/local /usr/local

# Create non-root user ─────────────────────────────────────────────────────────
ENV USER=omni
RUN adduser --disabled-password --gecos "" $USER
USER $USER
WORKDIR /home/$USER/app

# Copy application code (assumes repo root as Docker build context)
COPY --chown=$USER:$USER . .

# Environment ──────────────────────────────────────────────────────────────────
# • Everything works offline; OPENAI_API_KEY is optional.
ENV PYTHONUNBUFFERED=1 \
    OMNI_LEDGER=/home/$USER/app/omni_ledger.sqlite \
    LEDGER_PATH=${OMNI_LEDGER} \
    PROM_PORT=9137 \
    DASH_SERVER_PORT=8050 \
    AGI_TOKEN_SYMBOL="$AGIALPHA" \
    # Disables telemetry / cache in constrained environments
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1

# Ports
EXPOSE 8050 9137

# Health-check – verifies dashboard & metrics endpoints
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s CMD \
  curl -fsS http://localhost:${DASH_SERVER_PORT}/ || exit 1 && \
  curl -fsS http://localhost:${PROM_PORT}/metrics || exit 1

# SBOM (Software Bill of Materials) – optional, created at build time
RUN python -m pip install --no-cache-dir cyclonedx-bom==3.* && \
    cyclonedx-py -o /home/$USER/app/SBOM.cdx.json || true

# Entrypoint ───────────────────────────────────────────────────────────────────
# • Starts: 1) multi-agent core  2) Prometheus exporter  3) Dash UI
CMD python -m alpha_factory_v1.demos.omni_factory_demo & \
    python alpha_factory_v1/demos/omni_factory_demo/omni_metrics_exporter.py --port ${PROM_PORT} & \
    exec python alpha_factory_v1/demos/omni_factory_demo/omni_dashboard.py
