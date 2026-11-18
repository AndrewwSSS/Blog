COMPOSE ?= docker compose
API     ?= api

.DEFAULT_GOAL := help
.PHONY: help env install build up down restart ps logs shell test test-local migrate migration clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from .env.template (never overwrites an existing .env)
	@test -f .env && echo ".env already exists, not touching it" || (cp .env.template .env && echo "Created .env, fill in the required values")

install: ## Install dependencies locally with Poetry
	poetry install --no-root

build: ## Build the Docker images
	$(COMPOSE) build

up: ## Start all services in the background
	$(COMPOSE) up --build -d

down: ## Stop all services (keeps volumes and data)
	$(COMPOSE) down

restart: down up ## Restart all services

ps: ## Show service status
	$(COMPOSE) ps

logs: ## Follow logs (one service: make logs s=api)
	$(COMPOSE) logs -f $(s)

shell: ## Open a shell in the API container
	$(COMPOSE) exec $(API) bash

test: ## Run tests in the API container (services must be up)
	$(COMPOSE) exec $(API) pytest tests/

test-local: ## Run tests locally with Poetry
	poetry run pytest tests/

migrate: ## Apply database migrations
	$(COMPOSE) exec $(API) alembic upgrade head

migration: ## Create a migration: make migration m="add index"
	@test -n "$(m)" || (echo 'Usage: make migration m="message"' && exit 1)
	$(COMPOSE) exec $(API) alembic revision --autogenerate -m "$(m)"

clean: ## Remove local caches and the SQLite test database
	find . -type d -name __pycache__ -not -path './.venv/*' -prune -exec rm -rf {} +
	rm -rf .pytest_cache test_database.db
