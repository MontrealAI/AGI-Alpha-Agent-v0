# SPDX-License-Identifier: Apache-2.0
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}
LABEL org.opencontainers.image.title="Business 3 Enterprise Studio" \
      org.opencontainers.image.source="https://github.com/MontrealAI/AGI-Alpha-Agent-v0"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY alpha_factory_v1/__init__.py alpha_factory_v1/__init__.py
COPY alpha_factory_v1/demos/__init__.py alpha_factory_v1/demos/__init__.py
COPY alpha_factory_v1/utils/__init__.py alpha_factory_v1/utils/disclaimer.py alpha_factory_v1/utils/DISCLAIMER_SNIPPET.md alpha_factory_v1/utils/
COPY alpha_factory_v1/demos/alpha_agi_business_3_v1/ alpha_factory_v1/demos/alpha_agi_business_3_v1/
RUN useradd --uid 10001 --create-home appuser && mkdir /output && chown appuser:appuser /output
USER 10001:10001
WORKDIR /output
ENTRYPOINT ["python", "-m", "alpha_factory_v1.demos.alpha_agi_business_3_v1"]
CMD ["--output", "/output"]
