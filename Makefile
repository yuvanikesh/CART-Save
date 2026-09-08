# CartGuard AI - Development Makefile
# Per MASTER_PROMPT.md Section 17: Docker Compose and Local Developer Experience
# Usage: make setup, make up, make test, make clean-local

.PHONY: setup up down seed test test-integration build lint typecheck clean-local all

# Setup: Install dependencies
setup:
	@echo "📦 Installing dependencies..."
	pnpm install
	@echo "✅ Setup complete!"

# Start all services (Docker Compose)
up:
	@echo "🚀 Starting services..."
	docker compose up -d
	@echo "✅ Services running. Check health: docker compose ps"

# Stop all services
down:
	@echo "🛑 Stopping services..."
	docker compose down
	@echo "✅ Services stopped."

# Seed demo data (placeholder for Phase 1)
seed:
	@echo "🌱 Seeding demo tenant data..."
	@echo "TODO: Implement seed script in Phase 1"

# Build all packages
build:
	@echo "🔨 Building packages..."
	pnpm build
	@echo "✅ Build complete!"

# Run tests
test:
	@echo "🧪 Running tests..."
	pnpm test
	@echo "✅ Tests passed!"

# Run integration tests (placeholder for Phase 1)
test-integration:
	@echo "🧪 Running integration tests..."
	@echo "TODO: Implement integration tests in Phase 1"

# Lint code
lint:
	@echo "🔍 Linting code..."
	pnpm lint
	@echo "✅ Lint passed!"

# Type check
typecheck:
	@echo "📝 Type checking..."
	pnpm typecheck
	@echo "✅ Type check passed!"

# Clean local environment
clean-local:
	@echo "🧹 Cleaning local environment..."
	docker compose down -v
	rm -rf node_modules packages/*/node_modules apps/*/node_modules
	rm -rf packages/*/dist apps/*/dist
	@echo "✅ Clean complete!"

# Run everything: setup, up, build, test
all: setup up build test
	@echo "✅ CartGuard AI is ready!"
	@echo "Services: http://localhost:8000"
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"
	@echo "Redpanda: localhost:19092"

