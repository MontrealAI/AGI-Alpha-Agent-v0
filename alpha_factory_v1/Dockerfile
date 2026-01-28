# SPDX-License-Identifier: Apache-2.0
# syntax=docker/dockerfile:1.6
##############################################################################
#  Alpha‑Factory v1 👁️✨ — Multi‑Agent AGENTIC α‑AGI                         #
#  Universal Runtime Image (CPU‑only by default, CUDA optional)              #
#                                                                            #
#  • Stage 0  ─ Build the Trace‑graph web UI with Node/Vite (if present).    #
#  • Stage 1  ─ Hardened Python runtime with the OpenAI Agents SDK,          #
#               Google ADK (optional), and all project deps pre‑installed.   #
#                                                                            #
#  Build switches                                                            #
#  ─────────────────────────────────────────────────────────────────────────  #
#  BASE_IMAGE           ‑ Parent image for Stage 1 (default python:3.13).    #
#                        Pass  nvidia/cuda:12.4.0-runtime‑ubuntu22.04        #
#                        for a GPU‑enabled variant.                          #
#  INSTALL_UI           ‑ Set to "0" to skip the UI build stage.           #
##############################################################################

#######################################################################
#  Global ARGs must precede every FROM that references them           #
#######################################################################
ARG BASE_IMAGE=python:3.13-slim
ARG INSTALL_UI=1

#######################################################################
#  Stage 0 — (optional) Build static Trace‑graph front‑end            #
#######################################################################
FROM node:22.17.1-bookworm-slim AS ui-build
ARG INSTALL_UI
RUN if [ "$INSTALL_UI" = "0" ]; then echo "Skipping UI build stage" && exit 0; fi
WORKDIR /ui
COPY ui/package*.json ./          # leverage Docker layer cache
RUN if [ "$INSTALL_UI" = "1" ]; then npm ci --omit=dev; fi
COPY ui/ .
RUN if [ "$INSTALL_UI" = "1" ]; then npm run build; fi             # → dist/

#######################################################################
#  Stage 1 — Python Runtime                                           #
#######################################################################
FROM ${BASE_IMAGE} AS runtime
LABEL org.opencontainers.image.title="Alpha-Factory Runtime" \
      org.opencontainers.image.source="https://github.com/MontrealAI/AGI-Alpha-Agent-v0"

#############################
# 1) Environment variables   #
#############################
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app \
    GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git \
    API_TOKEN=REPLACE_ME_TOKEN \
    PATH="/usr/bin:$PATH"

#############################
# 2) System packages         #
#############################
# gcc & make  → compile Python wheels
# libopenblas + libomp → faiss‑cpu & numpy optimised BLAS
# git          → self‑healing demo (patch commit)
# curl, ca‑certificates → health‑check & diagnostics
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        libopenblas0 \
        libomp5 \
        libstdc++6 \
        postgresql-client \
        patch \  # required by the self-healing demo
        curl ca-certificates && \
    git --version && \
    rm -rf /var/lib/apt/lists/*

#############################
# 3) Python dependencies     #
#############################
WORKDIR /app

# -- Strict, reproducible lock (if present) ---------------------------
COPY requirements-lock.txt /tmp/requirements-lock.txt
# -- Project top‑level requirements (edited by humans) ----------------
COPY backend/requirements.txt /tmp/requirements.txt

#  The lock file is preferred (if the project maintains one).  
#  Fallback to plain requirements for dev checkouts.
RUN if [ -f /tmp/requirements-lock.txt ]; then \
        pip install --no-cache-dir --require-hashes -r /tmp/requirements-lock.txt; \
    else \
        pip install --no-cache-dir -r /tmp/requirements.txt; \
    fi && \
    # ⬇ Explicitly ensure critical agent frameworks are present
    pip install --no-cache-dir \
        openai-agents>=0.0.17 \   # OpenAI Agents SDK (beta)
        "google-adk @ git+https://github.com/google/adk-python@main#egg=google-adk" \
        anthropic>=0.21 \
        gunicorn rocketry prometheus-client && \
    rm -rf /tmp/requirements-lock.txt /tmp/requirements.txt

#############################
# 4) Copy project source     #
#############################
COPY backend/        /app/backend/
COPY ui/             /app/ui/
COPY entrypoint.sh   /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

#############################
# 5) (optional) UI bundle    #
#############################
ARG INSTALL_UI
COPY --from=ui-build /ui/dist/ /app/static/trace/

#############################
# 6) Non-root user           #
#############################
RUN addgroup --system alphafactory && \
    adduser --system --ingroup alphafactory --home /app alphafactory && \
    chown -R alphafactory:alphafactory /app
USER alphafactory

#############################
# 7) Health‑check           #
#############################
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f \
    -H "Authorization: Bearer ${API_TOKEN}" http://localhost:8000/healthz || exit 1
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD-SHELL curl -f -H "Authorization: Bearer $API_TOKEN" http://localhost:8000/healthz || exit 1

#############################
# 8) Ports & Entrypoint      #
#############################
EXPOSE 8000 3000
CMD ["/app/entrypoint.sh"]
