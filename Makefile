# EvalForge Makefile — common developer tasks

.PHONY: help install test lint format run-api run-dashboard docker-up docker-down clean

# Default target
help:
	@echo ""
	@echo "  EvalForge — available commands"
	@echo "  ─────────────────────────────────────────"
	@echo "  make install       Install all dependencies locally"
	@echo "  make test          Run test suite"
	@echo "  make lint          Run ruff linter"
	@echo "  make format        Auto-format with black"
	@echo "  make run-api       Start FastAPI dev server"
	@echo "  make run-dashboard Start Streamlit dashboard"
	@echo "  make docker-up     Start all services via Docker Compose"
	@echo "  make docker-down   Stop all services"
	@echo "  make clean         Remove __pycache__ and .pytest_cache"
	@echo ""

install:
	pip install -r requirements-api.txt
	pip install -r requirements-dashboard.txt
	pip install ruff black

test:
	python -m pytest tests/ -v --tb=short

test-watch:
	python -m pytest tests/ -v --tb=short -f

lint:
	ruff check api/ tests/ dashboard/

format:
	black api/ tests/ dashboard/

run-api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

run-dashboard:
	streamlit run dashboard/app.py --server.port 8501

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf data/*.db 2>/dev/null || true
	@echo "✓ Cleaned"
