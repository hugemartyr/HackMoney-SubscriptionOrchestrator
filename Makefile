# Makefile for Yellow Network Integration Agent Project

.PHONY: help install dev backend dashboard editor clean

help:
	@echo "Available commands:"
	@echo "  make install   - Install dependencies for all components"
	@echo "  make dev       - Run all components simultaneously (Backend, Dashboard, Editor)"
	@echo "  make backend   - Run only the Backend (FastAPI)"
	@echo "  make dashboard - Run only the Agent-Nexus Dashboard (Vite on port 8080)"
	@echo "  make editor    - Run only the Yellow Agent Editor (Next.js on port 3000)"
	@echo "  make clean     - Remove node_modules and python cache"

install:
	@echo "Installing dependencies..."
	
	@cd agent-nexus && npm install
	@cd frontend && npm install

backend:
	@echo "Starting Backend on http://localhost:8000..."
	@cd backend && source .venv/bin/activate && python -m uvicorn main:app --reload

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
