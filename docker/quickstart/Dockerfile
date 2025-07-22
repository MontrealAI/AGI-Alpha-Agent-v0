# SPDX-License-Identifier: Apache-2.0
# Minimal runtime image for the quickstart script
FROM python:3.11.13-slim

# confirm git availability
RUN apt-get update && apt-get install -y --no-install-recommends git && git --version && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git
ENV PATH="/usr/bin:$PATH"

# Install Alpha-Factory with default extras
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock && rm /tmp/requirements.lock

# Copy package source and install in editable mode
COPY alpha_factory_v1 /app/alpha_factory_v1
COPY af_requests /app/af_requests
COPY pyproject.toml README.md /app/
RUN pip install --no-cache-dir .

# Provide example environment files
COPY alpha_factory_v1/.env.sample /app/.env.sample
COPY alpha_factory_v1/demos/alpha_agi_insight_v1/.env.sample /app/insight.env.sample

CMD ["alpha-factory", "--help"]
