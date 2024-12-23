# Stage 1: Build Stage
FROM python:3.10-slim AS build-stage

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

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Stage 2: Production Stage
FROM python:3.10-slim AS production-stage

# Set working directory
WORKDIR /app

# Copy only necessary files from build-stage
COPY --from=build-stage /app /app

# Ensure the runtime dependencies are available
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Expose port
EXPOSE 8000

# Set entrypoint
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
