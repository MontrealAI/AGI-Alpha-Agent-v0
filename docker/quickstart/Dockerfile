# SPDX-License-Identifier: Apache-2.0
# Minimal preserved research API. Build with the repository root as context.
FROM python:3.13-slim

# confirm git availability
RUN apt-get update && apt-get install -y --no-install-recommends git && git --version && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git
ENV PATH="/usr/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app \
    AF_MEMORY_DIR=/data/memory ALPHA_ENABLED_AGENTS=ping

# Install Alpha-Factory with default extras
COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock && \
    python -m pip check && rm /tmp/requirements.lock

# Run the preserved source with its own locked dependencies. The operator wheel
# has a separate requirements-agent.lock profile; do not mix those environments.
COPY alpha_factory_v1 /app/alpha_factory_v1
COPY af_requests /app/af_requests
COPY openai_agents /app/openai_agents
COPY docker/quickstart/start.py /app/start.py
RUN printf '%s\n' '#!/bin/sh' 'exec python -m alpha_factory_v1.run "$@"' > /usr/local/bin/alpha-factory && \
    chmod 755 /usr/local/bin/alpha-factory

# Provide example environment files
COPY alpha_factory_v1/.env.sample /app/.env.sample
COPY alpha_factory_v1/demos/alpha_agi_insight_v1/.env.sample /app/insight.env.sample

RUN groupadd --gid 10001 alphafactory && \
    useradd --uid 10001 --gid alphafactory --no-create-home alphafactory && \
    mkdir /data && chown alphafactory:alphafactory /data
USER 10001:10001
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=15s --retries=3 \
  CMD python /app/start.py --healthcheck
CMD ["python", "/app/start.py"]
