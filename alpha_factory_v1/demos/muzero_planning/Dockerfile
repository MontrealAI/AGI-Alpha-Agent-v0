# SPDX-License-Identifier: Apache-2.0
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 GRADIO_ANALYTICS_ENABLED=False
WORKDIR /app
COPY alpha_factory_v1/demos/muzero_planning/requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock \
    && useradd --uid 1001 --create-home demo
COPY alpha_factory_v1/__init__.py /app/alpha_factory_v1/__init__.py
COPY alpha_factory_v1/utils /app/alpha_factory_v1/utils
COPY alpha_factory_v1/demos/__init__.py /app/alpha_factory_v1/demos/__init__.py
COPY alpha_factory_v1/demos/muzero_planning /app/alpha_factory_v1/demos/muzero_planning
USER 1001:1001
EXPOSE 7861
CMD ["python", "-m", "alpha_factory_v1.demos.muzero_planning", "--host", "0.0.0.0"]
