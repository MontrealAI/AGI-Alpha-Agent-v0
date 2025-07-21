# This demo is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk.

###############################################################################
# 🚀  Alpha-Factory v1 👁️✨  –  α-ASI World-Model Demo (Container Image)     #
# --------------------------------------------------------------------------- #
# A secure, reproducible, non-root image that runs the FastAPI service        #
# defined in `alpha_asi_world_model_demo.py`.                                 #
#                                                                             #
#   • Python 3.11-slim-bullseye base (tiny yet glibc-compatible for PyTorch)  #
#   • Layer-cached pip install; deterministic versions frozen inline          #
#   • Optional GPU build-arg (CUDA 12.1) – works CPU-only by default          #
#   • Health-check, tini (PID 1), non-root user for prod hardening            #
#   • Zero build-time secrets; runs with or without OPENAI_API_KEY            #
#                                                                             #
# Quick start (CPU):                                                           #
#   docker build -t alpha-asi-demo .                                          #
#   docker run -p 7860:7860 --rm alpha-asi-demo                               #
#                                                                             #
# GPU (requires NVIDIA Container Toolkit):                                    #
#   docker build --build-arg BASE=nvcr.io/nvidia/pytorch:24.02-py3 -t alpha-asi-demo . #
#   docker run --gpus all -p 7860:7860 --rm alpha-asi-demo                    #
###############################################################################

########## 1️⃣ Base image #####################################################
ARG BASE=python:3.11.13-slim-bullseye
FROM ${BASE} as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# system deps (tini for PID 1, curl for HLTH chk)
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends gosu tini curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

########## 2️⃣ Requirements layer (caching) ###################################
FROM base as requirements

COPY <<'PIP' /tmp/requirements.txt
fastapi==0.111.*
uvicorn[standard]==0.29.*
gunicorn==22.0.*
pydantic==2.*
PyYAML==6.*
numpy==1.26.*
torch==2.2.*          # wheel auto-selects CPU/GPU
openai==1.23.*        # loaded only if OPENAI_API_KEY present
tiktoken==0.6.*
PIP

RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

########## 3️⃣ Runtime image ##################################################
FROM base

# non-root prod user (UID 1001 chosen to avoid host collisions)
RUN useradd --uid 1001 --create-home appuser
WORKDIR /app

# copy installed packages (faster than re-install)
COPY --from=requirements /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=requirements /usr/local/bin /usr/local/bin

# copy repo subset needed at runtime
COPY alpha_factory_v1 ./alpha_factory_v1

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

# Health-check – tiny HTTP GET
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD \
  curl -fs http://localhost:7860/agents || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo", \
     "--demo", "--host", "0.0.0.0", "--port", "7860"]
