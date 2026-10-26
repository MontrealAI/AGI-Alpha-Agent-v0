# SPDX-License-Identifier: Apache-2.0
# Supply the reviewed mcr.microsoft.com/playwright/python:v1.63.0-noble image by immutable digest.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
COPY examples/successor-workbench/computer/requirements.lock /opt/successor/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /opt/successor/requirements.lock
COPY alpha_factory_v1/core/runtime/successor/computer_worker.py /opt/successor/computer_worker.py
USER 1000:1000
ENV HOME=/tmp PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/opt/successor/computer_worker.py"]
