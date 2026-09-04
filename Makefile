# CartGuard AI - Makefile for easy setup
# Usage: make setup, make train, make start, make demo, make zip

.PHONY: setup train start-backend start-dashboard run-demo zip all

# Setup Python virtual environment and install deps
setup:
	cd backend && python -m venv venv
	cd backend && venv/Scripts/pip install -r requirements.txt
	cp .env.example .env
	@echo "✅ Setup complete! Edit .env to add your API keys."

# Train the ML model
train:
	cd backend && python -m venv venv 2>nul || true
	cd backend && venv/Scripts/python ..\scripts\train_model.py 10000

# Start backend API server
start-backend:
	cd backend && venv/Scripts/python main.py

# Start Streamlit dashboard
start-dashboard:
	cd dashboard && ..\backend\venv/Scripts/streamlit run app.py

# Run demo scenarios
demo:
	cd backend && venv/Scripts/python ..\scripts\run_demo.py

# Create zip for submission
zip:
	powershell Compress-Archive -Path . -DestinationPath ..\cartguard-ai-submission.zip -Force
	@echo "✅ Zip created: cartguard-ai-submission.zip"

# Run everything
all: setup train
	@echo "✅ CartGuard AI is ready!"
	@echo "Start backend: make start-backend"
	@echo "Start dashboard: make start-dashboard"
