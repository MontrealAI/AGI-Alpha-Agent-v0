# Demo container for α‑AGI Insight
FROM python:3.11.13-slim

# Install build tools for optional native extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg build-essential git && \
    git --version && \
    export NODE_VERSION=22.17.1 NODE_DIST=node-v22.17.1-linux-x64.tar.xz && \
    curl -fsSLO "https://nodejs.org/dist/v$NODE_VERSION/$NODE_DIST" && \
    curl -fsSLO "https://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt" && \
    grep " $NODE_DIST$" SHASUMS256.txt | sha256sum -c - && \
    tar -xJf "$NODE_DIST" -C /usr/local --strip-components=1 && \
    rm "$NODE_DIST" SHASUMS256.txt && \
    ln -s /usr/local/bin/node /usr/local/bin/nodejs && \
    rm -rf /var/lib/apt/lists/*

# Verify Node installation is exactly 22.17.1
RUN node --version

WORKDIR /app

# Install Python dependencies for the demo
# The build context is the demo directory so copy the lock file directly
COPY ./requirements.lock /tmp/requirements.lock
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
ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git
ENV PATH="/usr/bin:$PATH"
EXPOSE 8000 8501 6006
ENTRYPOINT ["entrypoint.sh"]
CMD ["web"]
