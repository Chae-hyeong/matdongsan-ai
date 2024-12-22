# Python Slim Base Image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements.txt to the working directory
COPY requirements.txt .

# Install system dependencies for ffmpeg and other tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (including boto3)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 8000

# Set entrypoint
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]