# Demo container for α‑AGI Insight
FROM python:3.11-slim

# Install build tools for optional native extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g pnpm && \
    rm -rf /var/lib/apt/lists/*

# Verify Node installation is >=20 (NodeSource script sets up latest LTS)
RUN node --version

WORKDIR /app

# Install Python dependencies for the demo
COPY alpha_factory_v1/demos/alpha_agi_insight_v1/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock && rm /tmp/requirements.lock

# Copy the project source
COPY . /app
RUN pnpm --dir alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client install \
    && pnpm --dir alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client run build \
    && rm -rf alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client/node_modules

# copy built assets
COPY alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client/dist/ \
    /app/alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client/dist/

# Add non-root user and entrypoint
RUN adduser --disabled-password --gecos '' afuser && chown -R afuser /app
COPY alpha_factory_v1/demos/alpha_agi_insight_v1/infrastructure/docker-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
USER afuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000 8501 6006
ENTRYPOINT ["entrypoint.sh"]
CMD ["web"]
