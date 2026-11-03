FROM python:3.12-slim

WORKDIR /app

# Lesson plan PDF export renders through headless Chromium.  The slim base image
# has no CJK fonts, so Chinese text would print as empty boxes without them.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
# Browser binaries are large; install them here so the API process can render
# lesson plan PDFs without a separate sidecar image.
RUN playwright install --with-deps chromium

COPY . /app/backend
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend
