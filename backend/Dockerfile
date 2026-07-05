# Backend: FastAPI + uvicorn on Python 3.12 slim.
FROM python:3.12-slim

# Avoid interactive prompts, ensure logs flush immediately.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System deps for psycopg2-binary are already bundled, but curl is handy
# for the container healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY app ./app

EXPOSE 8000

# Uvicorn serves the FastAPI app. Host 0.0.0.0 so it's reachable across
# the Docker network.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
