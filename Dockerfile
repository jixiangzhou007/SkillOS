FROM python:3.12-slim

WORKDIR /app

# Install system deps for Playwright (optional E2E testing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[desktop]" && pip install pytest ruff

# Copy app
COPY . .

# Create data directory
RUN mkdir -p data

EXPOSE 8765

ENV SKILLOS_HOST=0.0.0.0
ENV SKILLOS_PORT=8765

CMD ["python", "-m", "skillos.ui.app", "--server-only", "--host", "0.0.0.0", "--port", "8765"]
