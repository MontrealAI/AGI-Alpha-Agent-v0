FROM python:3.11-slim

# install build tools and pnpm for the React UI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg build-essential postgresql-client && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g pnpm && \
    rm -rf /var/lib/apt/lists/*

# Verify Node installation is >=20 (NodeSource script sets up latest LTS)
RUN node --version

WORKDIR /app

# install Python dependencies
COPY alpha_factory_v1/demos/alpha_agi_insight_v1/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock && rm /tmp/requirements.lock

# copy minimal package files for the Insight demo
RUN mkdir -p alpha_factory_v1/demos
COPY alpha_factory_v1/__init__.py alpha_factory_v1/__init__.py
COPY alpha_factory_v1/demos/__init__.py alpha_factory_v1/demos/__init__.py
COPY alpha_factory_v1/demos/alpha_agi_insight_v1 alpha_factory_v1/demos/alpha_agi_insight_v1

# build the React front-end
RUN pnpm --dir alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client install \
    && pnpm --dir alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client run build \
    && rm -rf alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client/node_modules

# run as non-root user for demos
RUN useradd --uid 1001 --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
