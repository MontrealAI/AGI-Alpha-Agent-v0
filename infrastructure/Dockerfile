FROM python:3.13-slim

# install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential postgresql-client git \
    && git --version \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install Python dependencies using the pinned lock file
COPY alpha_factory_v1/backend/requirements-lock.txt /tmp/requirements.lock
COPY alpha_factory_v1/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.lock && rm /tmp/requirements.lock \
    && rm /tmp/requirements.txt

# copy project source
COPY . /app
# install project in editable mode
RUN pip install --no-cache-dir -e /app
# copy pre-built React bundle if available
COPY alpha_factory_v1/core/interface/web_client/dist/ \
     /app/alpha_factory_v1/core/interface/web_client/dist/

# add non-root user
RUN adduser --disabled-password --gecos '' afuser && chown -R afuser /app
COPY infrastructure/docker-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
USER afuser

ENV PATH="/usr/bin:/usr/local/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV GIT_PYTHON_REFRESH=quiet
ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# verify the API server is responsive
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD \
  curl -fsS http://localhost:8000/api/runs || exit 1

EXPOSE 8000 8501 6006
ENTRYPOINT ["entrypoint.sh"]
CMD ["web"]
