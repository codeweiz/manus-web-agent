FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package installation
RUN pip install uv

# Copy requirements first for better caching
COPY pyproject.toml .
COPY README.md .

# Install dependencies using uv
RUN uv pip install --system -e .

# Install playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy project files
COPY src/ ./src/
COPY .config.toml .

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Start command
CMD ["python", "-m", "manus_web_agent.main"]
