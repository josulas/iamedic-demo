FROM python:3.12-slim

# Set working directory
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Copy application files
COPY . .

# Transfer ownership of the application directory to the non-root user
RUN chown -R appuser:appuser /app

# Create a directory for model downloads with proper permissions
RUN mkdir -p /app/models && chown -R appuser:appuser /app/models

# Switch to the non-root user
USER appuser

# Expose the port FastAPI runs on
EXPOSE 8000

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]