FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY polyvox ./polyvox

RUN useradd -m -u 1000 appuser \
    && mkdir -p /data/audio \
    && chown -R appuser:appuser /app /data/audio /home/appuser
USER appuser
ENV PYTHONUNBUFFERED=1 HOME=/home/appuser

EXPOSE 8000
CMD ["uvicorn", "polyvox.main:app", "--host", "0.0.0.0", "--port", "8000"]
