# Makefile for Yellow Network Integration Agent Project

.PHONY: help install dev backend backend-setup dashboard editor clean

help:
	@echo "Available commands:"
	@echo "  make install        - Install dependencies for all components"
	@echo "  make backend-setup  - Create Python venv and install backend deps"
	@echo "  make backend       - Run the Backend (FastAPI via uvicorn)"
	@echo "  make dev           - Run all components simultaneously (Backend, Dashboard, Editor)"
	@echo "  make dashboard     - Run only the Agent-Nexus Dashboard (Vite on port 8080)"
	@echo "  make editor        - Run only the Yellow Agent Editor (Next.js on port 3000)"
	@echo "  make clean         - Remove node_modules and python cache"

install:
	@echo "Installing dependencies..."
	@$(MAKE) backend-setup
	@cd agent-nexus && npm install --force
	@cd frontend && npm install --force

backend-setup:
	@echo "Setting up Backend Python venv..."
	@cd backend && \
		if [ ! -d .venv ]; then \
			python3 -m venv .venv; \
			echo "Created .venv"; \
		fi && \
		. .venv/bin/activate && \
		pip install -r requirements.txt && \
		echo "Backend deps installed."

backend:
	@echo "Starting Backend on http://localhost:8000..."
	@cd backend && \
		if [ ! -d .venv ]; then \
			echo "Creating Python venv..."; \
			python3 -m venv .venv; \
			. .venv/bin/activate && pip install -r requirements.txt; \
		fi && \
		. .venv/bin/activate && \
		uvicorn main:app --reload --host 0.0.0.0 --port 8000

dashboard:
	@echo "Starting Agent-Nexus Dashboard on http://localhost:8080..."
	@cd agent-nexus && npm run dev

editor:
	@echo "Starting Yellow Agent Editor on http://localhost:3000..."
	@cd frontend && npm run dev

dev:
	@echo "Starting all services simultaneously..."
	@make -j 3 backend dashboard editor

clean:
	@echo "Cleaning up..."
	@rm -rf agent-nexus/node_modules
	@rm -rf frontend/node_modules
	@find . -type d -name "__pycache__" -exec rm -rf {} +
