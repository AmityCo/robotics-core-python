#!/bin/bash

# Azure App Service startup script for FastAPI application
echo "Starting FastAPI application..."

# Use Gunicorn with Uvicorn workers for production
exec gunicorn main:app \
  --bind 0.0.0.0:$PORT \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --timeout 300 \
  --keep-alive 2 \
  --max-requests 1000 \
  --max-requests-jitter 100