# Python Slim Base Image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements.txt to the working directory
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg for pydub
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Copy application filess
COPY . .

# Expose port
EXPOSE 8000

# Set entrypoint
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]