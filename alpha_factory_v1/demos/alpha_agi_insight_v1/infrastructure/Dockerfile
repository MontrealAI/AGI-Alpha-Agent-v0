# Demo container for α‑AGI Insight
FROM python:3.11.8-slim@sha256:90f8795536170fd08236d2ceb74fe7065dbf74f738d8b84bfbf263656654dc9b

# Install build tools for optional native extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Verify Node installation is >=20 (NodeSource script sets up latest LTS)
RUN node --version

WORKDIR /app

# Install Python dependencies for the demo
COPY requirements.lock /tmp/requirements.lock
# Installing without `--require-hashes` avoids failures when platform specific
# wheels are pulled in by pip. The lock file still pins exact versions.
RUN pip install --no-cache-dir -r /tmp/requirements.lock && rm /tmp/requirements.lock

# Copy the project source
COPY . /app
RUN npm ci --prefix src/interface/web_client \
    && npm --prefix src/interface/web_client run build \
    && rm -rf src/interface/web_client/node_modules

# Add non-root user and entrypoint
RUN adduser --disabled-password --gecos '' afuser && chown -R afuser /app
COPY ./infrastructure/docker-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
USER afuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000 8501 6006
ENTRYPOINT ["entrypoint.sh"]
CMD ["web"]
