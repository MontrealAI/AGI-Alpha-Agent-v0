# SPDX-License-Identifier: Apache-2.0
# When changing build dependencies here, mirror the updates in
# alpha_factory_v1/Dockerfile to keep both images consistent.
FROM python:3.13-slim
# Base image matches the highest Python version used in CI (currently 3.13)

# install build tools and Node.js 22.7.0 for the React UI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg build-essential git \
        rustc cargo postgresql-client patch && \
    git --version && \
    export NODE_VERSION=22.7.0 NODE_DIST=node-v22.7.0-linux-x64.tar.xz && \
    curl -fsSLO "https://nodejs.org/dist/v$NODE_VERSION/$NODE_DIST" && \
    curl -fsSLO "https://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt" && \
    grep " $NODE_DIST$" SHASUMS256.txt | sha256sum -c - && \
    tar -xJf "$NODE_DIST" -C /usr/local --strip-components=1 && \
    rm "$NODE_DIST" SHASUMS256.txt && \
    ln -s /usr/local/bin/node /usr/local/bin/nodejs && \
    rm -rf /var/lib/apt/lists/*

# upgrade pip to avoid outdated versions
RUN python -m pip install --upgrade "pip<25" setuptools wheel

# Verify Node installation is exactly 22.7.0
RUN node --version

WORKDIR /app

# ensure latest pip before installing requirements
RUN python -m pip install --upgrade pip

# install backend dependencies using the lock file
COPY alpha_factory_v1/backend/requirements-lock.txt /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock && rm /tmp/requirements.lock

# install Python dependencies
# Install demo-specific Python dependencies
COPY alpha_factory_v1/demos/alpha_agi_insight_v1/requirements.lock /tmp/requirements-demo.lock
RUN if [ -f /tmp/requirements-demo.lock ]; then \
      pip install --no-cache-dir --require-hashes -r /tmp/requirements-demo.lock && rm /tmp/requirements-demo.lock; \
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

# git executable path for GitPython
ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git
ENV PATH="/usr/bin:$PATH"

# run as non-root user for demos
RUN useradd --uid 1001 --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
