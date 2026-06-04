FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Port (Cloud Run injects $PORT, default 8080)
ENV PORT=8080
EXPOSE 8080

# Start with gunicorn (threaded for WebSocket support)
CMD exec gunicorn wsgi:app \
    --bind "0.0.0.0:$PORT" \
    --workers 1 \
    --threads 4 \
    --worker-class gthread \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
