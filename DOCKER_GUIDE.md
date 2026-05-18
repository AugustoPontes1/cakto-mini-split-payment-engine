# Docker Setup Guide

## 📋 Visão Geral

```
Dockerfile.dev    → Development (runserver, hot reload)
Dockerfile.stag   → Staging (Gunicorn, multi-stage build)
Dockerfile.prod   → Production (Gunicorn + optimized)

docker-compose.dev.yml   → Local development (Docker Compose)
docker-compose.stag.yml  → Staging environment (Docker Swarm)
docker-compose.prod.yml  → Production environment (Docker Swarm)
```

---

## 🚀 Quick Start

### **Development (Local)**

```bash
# Iniciar ambiente de dev
make dev

# A API estará rodando em http://localhost:8000
# Banco de dados em localhost:5432
```

Esse comando:
- ✅ Cria container PostgreSQL
- ✅ Cria container Django (com hot reload)
- ✅ Conecta os containers em rede bridge
- ✅ Volume mount (mudanças no código atualizam al servidor)

### **Rodar Testes**

```bash
make test
```

### **Parar Ambiente**

```bash
make down
```

---

## 🔷 Staging (Docker Swarm)

### **Inicializar Swarm (uma vez)**

```bash
make stag-init
```

Isso executa `docker swarm init` na sua máquina.

### **Deploy para Staging**

```bash
make stag-deploy
```

Isso:
- ✅ Faz build da imagem Docker
- ✅ Cria 2 replicas da aplicação (load balancing)
- ✅ Cria PostgreSQL em modo manager
- ✅ Cria Nginx para reverse proxy
- ✅ Usa overlay network

### **Verificar Status**

```bash
make stag-ps
```

Resultado esperado:
```
ID            NAME                 IMAGE       ...
xyz           cakto-stag_db.1      postgres:15
abc           cakto-stag_app.1     cakto:stag
def           cakto-stag_app.2     cakto:stag
ghi           cakto-stag_nginx.1   nginx:alpine
```

### **Ver Logs**

```bash
make stag-logs
```

### **Remover Staging**

```bash
make stag-down
```

---

## ⚙️ Production (Docker Swarm)

### **Deploy para Produção**

⚠️ **IMPORTANTE**: Precisa de variáveis de ambiente configuradas

```bash
# Criar arquivo .env com:
SECRET_KEY=seu-secret-key-gerado
DB_PASSWORD=senha-forte-do-banco
ALLOWED_HOSTS=seu-dominio.com,www.seu-dominio.com
DOCKER_USERNAME=seu-usuario-docker-hub
```

Depois:

```bash
make prod-deploy
```

Isso:
- ✅ Cria 3 replicas da aplicação (alta disponibilidade)
- ✅ PostgreSQL gerenciado em modo manager
- ✅ 2 instâncias Nginx
- ✅ Health checks em cada container
- ✅ Auto-restart em caso de falha
- ✅ Resource limits (CPU/Memory)
- ✅ Logging centralizado

### **Verificar Status**

```bash
make prod-ps
```

### **Ver Logs**

```bash
make prod-logs
```

### **Remover Production**

```bash
make prod-down
```

---

## 📦 Dockerfiles Explicados

### **Dockerfile.dev**

```dockerfile
FROM python:3.13-slim
# Instala dependências
# Copia código
# CMD: python manage.py runserver
```

**Características:**
- ✅ Simples e rápido para dev
- ✅ Inclui ipython, ipdb, django-extensions
- ✅ Volume mount permite hot reload
- ✅ DEBUG=true

**Use para:** Desenvolvimento local

---

### **Dockerfile.stag**

```dockerfile
FROM python:3.13-slim as builder
# Build stage: instala deps
FROM python:3.13-slim
# Final stage: copia apenas o necessário
# CMD: gunicorn
```

**Características:**
- ✅ Multi-stage build (imagem menor)
- ✅ Gunicorn + 4 workers
- ✅ Collectstatic automático
- ✅ DEBUG=false
- ✅ User não-root

**Use para:** Staging/testing antes de prod

---

### **Dockerfile.prod**

```dockerfile
FROM python:3.13-slim as builder
# Build stage
FROM python:3.13-slim
# Final stage: otimizado para produção
# CMD: gunicorn com logging
# HEALTHCHECK: curl /health/
```

**Características:**
- ✅ Multi-stage build
- ✅ Apenas pacotes necessários
- ✅ Gunicorn com logging estruturado
- ✅ Health check automático
- ✅ PYTHONUNBUFFERED=1
- ✅ User não-root (appuser)
- ✅ Imagem ~200MB

**Use para:** Produção em servidor real

---

## 🔗 Docker Compose Explicado

### **docker-compose.dev.yml**

```yaml
services:
  db:
    image: postgres:15-alpine
    # Local: 5432
    # Network: bridge
    # Health: pg_isready
  
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    # Port: 8000
    # Volume mount: ./:/app (hot reload)
    # Network: bridge
```

**Uso:**
```bash
docker-compose -f docker-compose.dev.yml up -d
```

---

### **docker-compose.stag.yml**

```yaml
services:
  db:
    # PostgreSQL em modo Swarm
    # Deploy: manager only
    # Replicas: 1
  
  app:
    # Gunicorn
    # Deploy: 2 replicas
    # Health check: curl /health/
    # Resources: limits + reservations
  
  nginx:
    # Reverse proxy
    # Port: 80, 443
    # Deploy: 1 replica
```

**Uso:**
```bash
docker stack deploy -c docker-compose.stag.yml cakto-stag
```

---

### **docker-compose.prod.yml**

```yaml
services:
  db:
    # PostgreSQL gerenciado
    # Deploy: manager only
    # Backups: /backups
    # Resources: 1 CPU, 1GB RAM
  
  app:
    # Gunicorn otimizado
    # Deploy: 3 replicas
    # Update: rolling, 1 de cada vez
    # Logging: json-file com rotation
  
  nginx:
    # Load balancer + reverse proxy
    # Deploy: 2 replicas
    # SSL/TLS: /etc/letsencrypt
```

**Uso:**
```bash
docker stack deploy -c docker-compose.prod.yml cakto-prod
```

---

## 🔐 Variáveis de Ambiente

### **Desenvolvimento (.env para docker-compose.dev.yml)**

```bash
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=postgresql://dev:dev@db:5432/cakto
ALLOWED_HOSTS=localhost,127.0.0.1
```

### **Staging (export antes de deploy)**

```bash
export SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
export DB_PASSWORD=staging-password-123
export DOCKER_USERNAME=seu-docker-user

docker stack deploy -c docker-compose.stag.yml cakto-stag
```

### **Production (arquivo .env.local)**

```bash
SECRET_KEY=random-secret-key-gerado
DB_PASSWORD=senha-forte-do-banco
ALLOWED_HOSTS=api.seu-dominio.com
DOCKER_USERNAME=seu-docker-user
```

---

## 🔥 Health Checks

Todos os serviços têm health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**Implementar no Django:**

```python
# app/api/views.py
from rest_framework.response import Response
from rest_framework.views import APIView

class HealthCheckView(APIView):
    def get(self, request):
        return Response({"status": "ok"}, status=200)

# configs/urls.py
urlpatterns = [
    path("health/", HealthCheckView.as_view()),
    # ... outras rotas
]
```

---

## 📊 Nginx Configuration

O arquivo `nginx.conf` inclui:

- ✅ HTTP → HTTPS redirect
- ✅ Gzip compression
- ✅ Security headers
- ✅ Load balancing (upstream)
- ✅ Static files caching
- ✅ SSL/TLS ready
- ✅ Rate limiting ready

**Customizar SSL:**

```nginx
# Editar em nginx.conf
ssl_certificate /etc/letsencrypt/live/seu-dominio/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/seu-dominio/privkey.pem;
```

---

## 🚨 Troubleshooting

### **Containers não sobem**

```bash
# Ver logs
docker-compose -f docker-compose.dev.yml logs app

# Validar compose file
docker-compose -f docker-compose.dev.yml config
```

### **Banco de dados não conecta**

```bash
# Verificar se DB está healthy
docker-compose -f docker-compose.dev.yml ps db

# Conectar manualmente
psql postgresql://dev:dev@localhost:5432/cakto
```

### **Porta já em uso**

```bash
# Ver o que tá usando porta 8000
lsof -i :8000

# Ou mudar no docker-compose.yml
ports:
  - "8001:8000"  # Usar 8001 ao invés
```

### **Docker Swarm não inicializa**

```bash
# Se tá em erro, limpar
docker swarm leave --force

# Reinicializar
docker swarm init
```

---

## 📈 Scaling

### **Staging: aumentar replicas**

```yaml
# docker-compose.stag.yml
app:
  deploy:
    replicas: 5  # aumentar de 2 para 5
```

Depois redeploy:
```bash
docker stack deploy -c docker-compose.stag.yml cakto-stag
```

---

## 🧹 Limpeza

```bash
# Remover containers locais
make down

# Remover stacks Swarm
make stag-down
make prod-down

# Limpeza completa (⚠️ cuidado!)
make clean
```

---

## 📝 Resumo de Comandos

| Comando | O que faz |
|---------|-----------|
| `make dev` | Inicia dev local |
| `make test` | Roda testes |
| `make stag-deploy` | Deploy em staging |
| `make prod-deploy` | Deploy em produção |
| `make logs` | Ver logs da app |
| `make clean` | Limpar tudo |

