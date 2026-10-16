FROM python:3.11-slim

# Required only for converting completed PPM Excel checklists to PDF pages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-calc fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements_backend.txt /app/requirements_backend.txt
RUN pip install --no-cache-dir -r /app/requirements_backend.txt
COPY . /app
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
