.PHONY: help dev test migrate clean down logs install-docker-compose

help:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║   Cakto Mini Split Engine - Development Commands           ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Setup:"
	@echo "  make install-docker-compose  Install Docker Compose v2"
	@echo ""
	@echo "Local Development:"
	@echo "  make dev              Build and start dev environment"
	@echo "  make test             Run tests"
	@echo "  make migrate          Run Django migrations"
	@echo "  make shell            Django shell"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run all linters (flake8, mypy)"
	@echo "  make format           Format code (black, isort)"
	@echo "  make format-check     Check format without changing"
	@echo "  make pre-commit       Run pre-commit hooks manually"
	@echo ""
	@echo "Docker Compose:"
	@echo "  make down             Stop all containers"
	@echo "  make logs             View app logs"
	@echo "  make logs-db          View database logs"
	@echo ""
	@echo "Staging (Swarm):"
	@echo "  make stag-init        Initialize Docker Swarm"
	@echo "  make stag-deploy      Deploy to staging"
	@echo "  make stag-ps          Check staging services"
	@echo "  make stag-down        Remove staging services"
	@echo ""
	@echo "Production (Swarm):"
	@echo "  make prod-deploy      Deploy to production"
	@echo "  make prod-ps          Check production services"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove all containers and volumes"
	@echo ""

# ===== LOCAL DEVELOPMENT =====
dev:
	@echo "🚀 Starting development environment..."
	docker compose -f docker-compose.dev.yml up -d
	@echo "✅ Dev environment started!"
	@echo "📍 API: http://localhost:8000"
	@echo "💾 DB:  localhost:5432"
	@sleep 5
	@docker compose -f docker-compose.dev.yml logs app | head -20

# ===== SETUP =====
install-docker-compose:
	@echo "📦 Installing Docker Compose v2..."
	@mkdir -p ~/.docker/cli-plugins
	@curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-$$(uname -s)-$$(uname -m) -o ~/.docker/cli-plugins/docker-compose
	@chmod +x ~/.docker/cli-plugins/docker-compose
	@echo "✅ Docker Compose v2 installed!"
	@echo "Verify with: docker compose --version"

test:
	@echo "🧪 Running tests..."
	docker compose -f docker-compose.dev.yml exec app python manage.py test app.api.tests -v 2

migrate:
	@echo "🔄 Running migrations..."
	docker compose -f docker-compose.dev.yml exec app python manage.py migrate

makemigrations:
	@echo "📝 Creating migrations..."
	docker compose -f docker-compose.dev.yml exec app python manage.py makemigrations

shell:
	@echo "🐚 Opening Django shell..."
	docker compose -f docker-compose.dev.yml exec app python manage.py shell

createsuperuser:
	@echo "👤 Creating superuser..."
	docker compose -f docker-compose.dev.yml exec app python manage.py createsuperuser

# ===== LOGGING =====
logs:
	docker compose -f docker-compose.dev.yml logs -f app

logs-db:
	docker compose -f docker-compose.dev.yml logs -f db

logs-all:
	docker compose -f docker-compose.dev.yml logs -f

# ===== CLEANUP =====
down:
	@echo "🛑 Stopping containers..."
	docker compose -f docker-compose.dev.yml down

clean:
	@echo "🗑️  Cleaning up Docker resources..."
	docker compose -f docker-compose.dev.yml down -v
	docker stack rm cakto-stag 2>/dev/null || true
	docker stack rm cakto-prod 2>/dev/null || true
	@echo "✅ Cleanup complete"

# ===== BUILD =====
build-dev:
	@echo "🔨 Building dev image..."
	docker build -f Dockerfile.dev -t cakto:dev .

build-stag:
	@echo "🔨 Building staging image..."
	docker build -f Dockerfile.stag -t cakto:stag .

build-prod:
	@echo "🔨 Building production image..."
	docker build -f Dockerfile.prod -t cakto:latest .

build-all: build-dev build-stag build-prod
	@echo "✅ All images built"

# ===== VERIFICATION =====
ps:
	@echo "🐳 Docker containers:"
	docker compose -f docker-compose.dev.yml ps

health-check:
	@echo "🏥 Checking health..."
	curl -s http://localhost:8000/health/ || echo "API not responding"

requirements:
	@echo "📦 Exporting requirements..."
	docker compose -f docker-compose.dev.yml exec app pip freeze > requirements.txt

# ===== CODE QUALITY =====
format:
	@echo "🎨 Formatting code with black and isort..."
	docker compose -f docker-compose.dev.yml exec app black app configs
	docker compose -f docker-compose.dev.yml exec app isort app configs
	@echo "✅ Code formatted"

format-check:
	@echo "🔍 Checking format without changing..."
	docker compose -f docker-compose.dev.yml exec app black --check app configs
	docker compose -f docker-compose.dev.yml exec app isort --check-only app configs

lint:
	@echo "🔎 Running linters..."
	docker compose -f docker-compose.dev.yml exec app flake8 app configs
	docker compose -f docker-compose.dev.yml exec app mypy app --ignore-missing-imports
	@echo "✅ Linting passed"

pre-commit:
	@echo "🪝 Running pre-commit hooks..."
	docker compose -f docker-compose.dev.yml exec app pre-commit run --all-files
	@echo "✅ Pre-commit passed"

security:
	@echo "🔐 Running security checks..."
	docker compose -f docker-compose.dev.yml exec app bandit -r app -f json
	@echo "✅ Security check passed"

full-check: format lint security test
	@echo "✅ All checks passed!"
