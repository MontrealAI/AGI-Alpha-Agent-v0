FROM python:3.11-slim

# install system deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install Python dependencies
# copy both requirement files so relative includes resolve during build
COPY requirements.txt alpha_factory_v1/requirements-core.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt /tmp/requirements-core.txt

# copy project source
COPY . /app
# copy pre-built React bundle if available
COPY alpha_factory_v1/core/interface/web_client/dist/ \
     /app/alpha_factory_v1/core/interface/web_client/dist/

# add non-root user
RUN adduser --disabled-password --gecos '' afuser && chown -R afuser /app
COPY infrastructure/docker-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
USER afuser

ENV PYTHONUNBUFFERED=1
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# verify the API server is responsive
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD \
  curl -fsS http://localhost:8000/api/runs || exit 1

EXPOSE 8000 8501 6006
ENTRYPOINT ["entrypoint.sh"]
CMD ["web"]
