FROM python:3.11-slim
WORKDIR /app
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock && rm /tmp/requirements.lock
COPY alpha_factory_v1/demos/alpha_agi_insight_v1 /app/alpha_factory_v1/demos/alpha_agi_insight_v1
EXPOSE 8000
CMD ["uvicorn", "alpha_factory_v1.demos.alpha_agi_insight_v1.src.evolution_worker:app", "--host", "0.0.0.0", "--port", "8000"]
