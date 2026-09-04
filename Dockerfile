FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Hugging Face Spaces expects port 7860 by default
ENV PORT=7860
ENV HOST=0.0.0.0

EXPOSE 7860

CMD ["python", "run_server.py", "--port", "7860", "--host", "0.0.0.0"]
