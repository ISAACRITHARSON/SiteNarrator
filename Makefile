.PHONY: dev demo test lint install clean frontend-install frontend-dev

# ─── Development ───────────────────────────────────────
install:
	pip install -r requirements.txt

dev:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# ─── Frontend ──────────────────────────────────────────
frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

# ─── Full Stack (API + Frontend) ───────────────────────
start: 
	@echo "Starting API server..."
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting frontend..."
	cd frontend && npm run dev

# ─── Demo ──────────────────────────────────────────────
demo:
	python demo/seed_data.py
	python demo/run_demo.py

# ─── Testing ──────────────────────────────────────────
test:
	python -m pytest tests/ -v

# ─── Linting ──────────────────────────────────────────
lint:
	python -m ruff check src/
	python -m ruff format --check src/

format:
	python -m ruff format src/

# ─── Cleanup ──────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
