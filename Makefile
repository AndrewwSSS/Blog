COMPOSE ?= docker compose
API     ?= api
PROD    := $(COMPOSE) -f docker-compose.yaml -f docker-compose.prod.yaml

.DEFAULT_GOAL := help
.PHONY: help env install build up up-debug up-prod down down-prod restart rebuild ps logs shell test test-local lint format migrate migration clean

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

up-debug: ## Start all services plus Flower (:5555) and Kibana (:5601)
	$(COMPOSE) --profile debug up --build -d

up-prod: ## Start the production stack behind Traefik (HTTPS on :443, needs DOMAIN in .env)
	$(PROD) up --build -d

down: ## Stop all services, including debug tools (keeps volumes and data)
	$(COMPOSE) --profile debug down

down-prod: ## Stop the production stack, including Traefik (keeps volumes and data)
	$(PROD) down

restart: down up ## Restart all services

rebuild: ## Rebuild images, recreate all containers in the background, then follow logs
	$(COMPOSE) up --build --force-recreate --remove-orphans -d
	$(COMPOSE) logs -f --tail=100

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

lint: ## Check code with ruff
	poetry run ruff check .

format: ## Format code with ruff
	poetry run ruff format .

migrate: ## Apply database migrations
	$(COMPOSE) exec $(API) alembic upgrade head

migration: ## Create a migration: make migration m="add index"
	@test -n "$(m)" || (echo 'Usage: make migration m="message"' && exit 1)
	$(COMPOSE) exec $(API) alembic revision --autogenerate -m "$(m)"

clean: ## Remove local caches and the SQLite test database
	find . -type d -name __pycache__ -not -path './.venv/*' -prune -exec rm -rf {} +
	rm -rf .pytest_cache test_database.db
