.PHONY: all up down ps logs rebuild

all: up

up:
	docker compose up --build -d

down:
	docker compose down --remove-orphans

ps:
	docker compose ps

logs:
	docker compose logs -f

rebuild:
	docker compose up --build -d --force-recreate
