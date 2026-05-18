.PHONY: help venv install up down logs ps rebuild run-demo

VENV_DIR := .venv
VENV_PY := $(VENV_DIR)/Scripts/python.exe

default: up

help:
	@echo "Targets:"
	@echo "  make         - Build and start all services"
	@echo "  make venv    - Create local Python virtual environment"
	@echo "  make install - Install Python dependencies into .venv"
	@echo "  make up      - Build and start all services"
	@echo "  make down    - Stop and remove all services"
	@echo "  make logs    - Follow compose logs"
	@echo "  make ps      - Show compose service status"
	@echo "  make rebuild - Rebuild and start all services"
	@echo "  make run-demo- Run demo_app.py from .venv"

venv:
	python -m venv $(VENV_DIR)

install: venv
	$(VENV_PY) -m pip install -r requirements.txt

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

rebuild:
	docker compose down
	docker compose up -d --build

run-demo: install
	$(VENV_PY) demo_app.py
