FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create models directory
RUN mkdir -p models

# Train model on startup if not exists
RUN python -c "from utils.synthetic_data import generate_synthetic_sessions; print('Data module OK')"

# Expose port
EXPOSE 8000

# Start server
CMD ["sh", "-c", "python -c 'from models.ensemble_model import train_and_save_model; train_and_save_model(5000)' && uvicorn main:app --host 0.0.0.0 --port 8000"]
