# SPDX-License-Identifier: Apache-2.0
# When changing build dependencies here, mirror the updates in
# alpha_factory_v1/Dockerfile to keep both images consistent.
FROM python:3.11.8-slim@sha256:90f8795536170fd08236d2ceb74fe7065dbf74f738d8b84bfbf263656654dc9b

# install build tools and npm for the React UI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg build-essential git \
        rustc cargo postgresql-client patch && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# upgrade pip to avoid outdated versions
RUN python -m pip install --upgrade "pip<25" setuptools wheel

# Verify Node installation is >=20 (NodeSource script sets up latest LTS)
RUN node --version

WORKDIR /app

# install Python dependencies
# Install demo-specific Python dependencies
COPY alpha_factory_v1/demos/alpha_agi_insight_v1/requirements.lock /tmp/requirements-demo.lock
RUN if [ -f /tmp/requirements-demo.lock ]; then \
      pip install --no-cache-dir -r /tmp/requirements-demo.lock && rm /tmp/requirements-demo.lock; \
    else \
      echo "Missing demo requirements" && exit 1; \
    fi
RUN pip install --no-cache-dir "openai_agents>=0.0.17"

# copy minimal package files for the Insight demo
RUN mkdir -p alpha_factory_v1/demos
COPY alpha_factory_v1/__init__.py alpha_factory_v1/__init__.py
COPY alpha_factory_v1/demos/__init__.py alpha_factory_v1/demos/__init__.py
COPY alpha_factory_v1/demos/alpha_agi_insight_v1 alpha_factory_v1/demos/alpha_agi_insight_v1
COPY alpha_factory_v1/demos/self_healing_repo alpha_factory_v1/demos/self_healing_repo
COPY alpha_factory_v1/demos/self_healing_repo_cli.py alpha_factory_v1/demos/self_healing_repo_cli.py

# build the React front-end
RUN npm ci --prefix alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client \
    && npm --prefix alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client run build \
    && rm -rf alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client/node_modules

# run as non-root user for demos
RUN useradd --uid 1001 --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
