FROM python:3.11.13-slim

WORKDIR /app

# Install demo dependencies
COPY ../../../requirements-demo.txt /tmp/requirements-demo.txt
RUN pip install --no-cache-dir -r /tmp/requirements-demo.txt \
    && pip install --no-cache-dir openai-agents==0.0.17 \
    && rm /tmp/requirements-demo.txt

# Copy only the demo package
RUN mkdir -p alpha_factory_v1/demos
COPY ../../__init__.py alpha_factory_v1/__init__.py
COPY ../../demos/__init__.py alpha_factory_v1/demos/__init__.py
COPY . alpha_factory_v1/demos/alpha_agi_business_3_v1

# Switch to non-root user
RUN useradd --uid 1001 --create-home appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "alpha_factory_v1.demos.alpha_agi_business_3_v1"]
