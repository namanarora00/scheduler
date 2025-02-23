FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /data
RUN chmod +x /app/scripts/start.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=app/app.py
ENV FLASK_ENV=development
ENV FLASK_RUN_PORT=6000

CMD ["/app/scripts/start.sh"]
