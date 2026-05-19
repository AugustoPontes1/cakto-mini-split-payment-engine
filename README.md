# Cakto Mini Split Engine

Mini engine de pagamentos para infoprodutos com suporte a cálculo de taxas, split de recebíveis, precisão financeira de centavos, idempotência e auditoria via outbox pattern.

## 🚀 Status

**✅ Completo e funcional**: API pronta para uso com Docker, testes automatizados, validações robustas e suporte a múltiplos ambientes.

## 🎯 Features

- ✅ Cálculo automático de taxas (PIX 0%, CARD 3.99%-26.99%)
- ✅ Split de recebíveis (1-5 recebedores)
- ✅ Precisão de centavos garantida
- ✅ Idempotência com detecção de conflitos (409)
- ✅ Ledger para auditoria completa
- ✅ Outbox Event Pattern para rastreabilidade
- ✅ Suporte a parcelamento (1-12x)
- ✅ Validações rigorosas de negócio
- ✅ Testes automatizados
- ✅ Docker multi-ambiente (dev, staging, prod)
- ✅ GitHub Actions CI/CD
- ✅ Pre-commit hooks (Black, isort, Flake8)

## 📋 Requisitos

- Python 3.13+
- PostgreSQL 15+
- Docker & Docker Compose v2
- Make (opcional, para usar Makefile)

## 🔧 Setup Local

### 1. Instalar Docker Compose v2

```bash
make install-docker-compose
```

Ou manualmente:
```bash
mkdir -p ~/.docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) \
  -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose
docker compose --version
```

### 2. Iniciar desenvolvimento

```bash
make dev
```

A API estará disponível em:
- **http://localhost:8000** (default)
- **http://localhost:8001** (se porta 8000 em uso)

Pode usar variáveis de ambiente:
```bash
PORT=8002 make dev
```

### 3. Executar migrações

```bash
make migrate
```

### 4. Rodar testes

```bash
make test
```

## 🌐 URLs de Deploy (Railway)

**Staging:**
```
https://triumphant-energy-staging.up.railway.app
```

**Production:**
```
https://cakto-mini-split-payment-engine-production.up.railway.app
```

### Exemplo de requisição para Staging

```bash
curl -X POST https://triumphant-energy-staging.up.railway.app/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-$(date +%s)" \
  -d '{
    "amount": "297.00",
    "currency": "BRL",
    "payment_method": "card",
    "installments": 3,
    "splits": [
      {"recipient_id": "p1", "role": "producer", "percent": 70},
      {"recipient_id": "a1", "role": "affiliate", "percent": 30}
    ]
  }'
```

### Exemplo de requisição para Production

```bash
curl -X POST https://cakto-mini-split-payment-engine-production.up.railway.app/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-$(date +%s)" \
  -d '{
    "amount": "297.00",
    "currency": "BRL",
    "payment_method": "card",
    "installments": 3,
    "splits": [
      {"recipient_id": "p1", "role": "producer", "percent": 70},
      {"recipient_id": "a1", "role": "affiliate", "percent": 30}
    ]
  }'
```

## 📡 API Endpoints

### POST /api/v1/payments

Confirmar pagamento com split automático.

**Headers obrigatórios:**
- `Content-Type: application/json`
- `Idempotency-Key: <unique-id>` ← OBRIGATÓRIO para idempotência

**Request:**
```json
{
  "amount": "297.00",
  "currency": "BRL",
  "payment_method": "card",
  "installments": 3,
  "splits": [
    { "recipient_id": "producer_1", "role": "producer", "percent": 70 },
    { "recipient_id": "affiliate_9", "role": "affiliate", "percent": 30 }
  ]
}
```

**Response (201 Created):**
```json
{
  "payment_id": "pmt_9661a833-4a74-4df5-8bd5-2acc6719fce1",
  "status": "captured",
  "gross_amount": "297.00",
  "platform_fee_amount": "26.70",
  "net_amount": "270.30",
  "receivables": [
    {
      "recipient_id": "producer_1",
      "role": "producer",
      "amount": 189.21
    },
    {
      "recipient_id": "affiliate_9",
      "role": "affiliate",
      "amount": 81.09
    }
  ],
  "outbox_event": {
    "type": "payment_captured",
    "status": "pending"
  },
  "created_at": "2026-05-18T23:51:13.154037+00:00"
}
```

**Exemplo com cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: pix-001-$(date +%s)" \
  -d '{
    "amount": "100.00",
    "currency": "BRL",
    "payment_method": "pix",
    "installments": 1,
    "splits": [
      {"recipient_id": "p1", "role": "producer", "percent": 100}
    ]
  }'
```

**Exemplo no Postman:**
1. Method: **POST**
2. URL: `http://127.0.0.1:8000/api/v1/payments`
3. Headers tab:
   - `Content-Type: application/json`
   - `Idempotency-Key: test-123`
4. Body tab: selecione **raw** → **JSON** (dropdown)
5. Cole o JSON acima

## 💰 Tabela de Taxas

| Método | Parcelas | Taxa Base | Taxa Extra | Total |
|--------|----------|-----------|-----------|-------|
| PIX | 1x | — | — | **0%** |
| CARD | 1x | 3.99% | — | **3.99%** |
| CARD | 2x | 4.99% | 2% | **6.99%** |
| CARD | 3x | 4.99% | 4% | **8.99%** |
| CARD | 4x | 4.99% | 6% | **10.99%** |
| CARD | 12x | 4.99% | 22% | **26.99%** |

## ✅ Validações

- `amount > 0` (obrigatório)
- `currency` ∈ [BRL] (default: BRL)
- `payment_method` ∈ [pix, card]
- `installments`:
  - PIX: obrigatoriamente **1**
  - CARD: **1-12**
- `splits`:
  - Quantidade: **1-5 recebedores**
  - Percentuais: cada um **> 0 e <= 100**
  - Soma: exatamente **100**
- `idempotency_key`: **obrigatório**, deve ser único

## 🔐 Decisões Técnicas

### 1. Precisão de Centavos

**Estratégia**: `Decimal` com `ROUND_DOWN` + absorção de resto no primeiro recebedor.

**Por quê**:
- `Decimal` evita erros de arredondamento de floats (0.1 + 0.2 ≠ 0.3 em float)
- `ROUND_DOWN` garante nunca ultrapassar o valor líquido
- O primeiro recebedor absorve centavos restantes (estratégia justa)
- **Invariante**: `sum(receivables) == net_amount` (sempre verdadeiro)

**Exemplo prático**:
```
net_amount = 100.00
splits: [33.33%, 33.33%, 33.34%]

Cálculo passo a passo:
- Recebedor 1: floor(100 × 0.3333) = 33.33
- Recebedor 2: floor(100 × 0.3333) = 33.33
- Recebedor 3: 100 - 33.33 - 33.33 = 33.34 (absorve o resto)

Resultado final: 33.33 + 33.33 + 33.34 = 100.00 ✅
Sem divergência!
```

**Implementação**:
```python
from decimal import Decimal, ROUND_DOWN

# Cálculo da taxa
fee_amount = (gross_amount * fee_percent / Decimal("100")).quantize(
    Decimal("0.01"), rounding=ROUND_DOWN
)
net_amount = gross_amount - fee_amount

# Distribuição do split
accumulated = Decimal("0.00")
for idx, split in enumerate(splits):
    if idx < len(splits) - 1:
        # Todos exceto o último: usar floor
        amount = (net_amount * split_percent / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
    else:
        # Último recebedor: absorve tudo que sobrou
        amount = net_amount - accumulated
    accumulated += amount

# Garantia
assert sum(receivables) == net_amount  # Sempre True
```

### 2. Estratégia de Idempotência

**Regras implementadas**:

| Cenário | Resposta |
|---------|----------|
| Sem `Idempotency-Key` header | **400 Bad Request** |
| Mesma key + mesmo payload | **200 OK** (retorna resultado anterior, sem duplicar) |
| Mesma key + payload diferente | **409 Conflict** |
| Chave nova | **201 Created** (novo pagamento) |

**Por quê**:
- Idempotência é crítica em pagamentos para evitar duplicatas
- Se conexão cai e cliente retry, não duplica pagamento
- 409 Conflict sinaliza erro para investigar
- Idempotency-Key obrigatório força bom padrão

**Código na view**:
```python
idempotency_key = request.headers.get("Idempotency-Key")
if not idempotency_key:
    return Response(
        {"error": "Idempotency-Key header is required"},
        status=status.HTTP_400_BAD_REQUEST
    )

existing = Payment.objects.filter(idempotency_key=idempotency_key).first()

if existing:
    if self._payloads_match(request.data, existing.payload):
        # Mesma key, mesmo payload → retorna anterior
        return Response(existing.to_dict(), status=status.HTTP_200_OK)
    else:
        # Mesma key, payload diferente → conflito
        return Response(
            {"error": "Idempotency conflict: same key, different payload"},
            status=status.HTTP_409_CONFLICT
        )
```

### 3. Auditoria com Ledger

Cada pagamento gera **um `LedgerEntry` por recebedor**, permitindo:
- Rastreamento de quanto cada recebedor recebeu
- Reconciliação entre sistemas
- Auditoria completa do split executado

```python
for receivable in calc_result["receivables"]:
    LedgerEntry.objects.create(
        payment=payment,
        recipient_id=receivable["recipient_id"],
        role=receivable["role"],
        amount=receivable["amount"],
    )
```

### 4. Outbox Event Pattern

Cada pagamento registra um **`OutboxEvent`** com status "pending", preparando para:
- Processamento assíncrono posterior
- Publicação em message brokers (Kafka, RabbitMQ, SQS)
- Integração com sistemas downstream (notificação, analytics)
- Garantia de entrega "at least once"

```python
OutboxEvent.objects.create(
    payment=payment,
    type="payment_captured",
    payload={...cálculos...},
    status="pending",
)
```

## 🧪 Testes

Testes implementados em `app/api/tests/`. Execute com:

```bash
make test
```

**Cobertura de testes**:

### test_split_calculator.py
- ✅ Validação: rejeita amount negativo
- ✅ Validação: PIX não aceita parcelamento
- ✅ Validação: splits devem somar 100%
- ✅ Precisão: PIX 0% com split 100% (bate exato)
- ✅ Precisão: CARD 3x com split 70/30 (sum receivables = net)
- ✅ Arredondamento: caso com sobra de centavos (0.01)

### test_views.py
- ✅ POST /payments com dados válidos → 201 Created
- ✅ Idempotência: mesma key + payload = 200 (não duplica)
- ✅ Idempotência: mesma key + payload diferente = 409

## 🚀 Pipeline CI/CD

### 1. Dev Tests (devtests.yml)

Executado **ao criar/atualizar um PR** para `develop`:

```bash
git push origin feature-branch
# → Cria PR contra develop
```

GitHub Actions roda em `.github/workflows/devtests.yml`:
- ✅ Black: validação de formatação
- ✅ isort: validação de imports
- ✅ Flake8: linting
- ✅ Unit tests: testes automatizados com PostgreSQL
- ✅ Coverage report: envio para Codecov

**Status**: ✅ Deve passar antes de fazer merge

### 2. Staging Deploy (deploystag.yml)

Executado **após merge de PR** em `develop`:

```bash
# 1. Abrir PR contra develop
# 2. Passes devtests ✅
# 3. Fazer merge do PR
# → Deploy automático em staging
```

GitHub Actions roda em `.github/workflows/deploystag.yml`:
- ✅ Roda testes (mesma suite que devtests)
- ✅ Faz deploy em Railway staging
- **Ambiente**: `RAILWAY_TOKEN_STAGING` + `RAILWAY_PROJECT_ID_STAGING`

### 3. Production Deploy (deployprod.yml)

Executado **após merge de PR** em `main`:

```bash
# 1. Abrir PR contra main (ex: develop → main)
# 2. Passes testes ✅
# 3. Fazer merge do PR
# → Deploy automático em production
```

GitHub Actions roda em `.github/workflows/deployprod.yml`:
- ✅ Roda testes (validação final)
- ✅ Faz deploy em Railway production
- **Ambiente**: `RAILWAY_TOKEN_PRODUCTION` + `RAILWAY_PROJECT_ID_PRODUCTION`

### Fluxo Git Recomendado

```
feature-branch (PR → develop)
       ↓
    devtests ✅
       ↓
    Merge em develop
       ↓
    deploystag 🚀 (staging)
       ↓
develop-branch (PR → main)
       ↓
    Merge em main
       ↓
    deployprod 🚀 (production)
```

**Importante**: Deploys são acionados por **merge de PR**, não por push direto. Isso garante code review antes de cada deploy.

### Configuração de Secrets no GitHub

Para que os workflows funcionem, configure no repositório:

1. **Staging** (Settings → Secrets and variables → Actions):
   - `RAILWAY_TOKEN_STAGING`: Token do Railway (staging)
   - `RAILWAY_PROJECT_ID_STAGING`: Project ID no Railway (staging)

2. **Production**:
   - `RAILWAY_TOKEN_PRODUCTION`: Token do Railway (production)
   - `RAILWAY_PROJECT_ID_PRODUCTION`: Project ID no Railway (production)

## 🛠️ Code Quality

### Pre-commit Hooks

Antes de cada commit, validações locais:

```bash
pip install pre-commit
pre-commit install
```

Executar manualmente:
```bash
pre-commit run --all-files
```

**Hooks configurados** (`.pre-commit-config.yaml`):
- 🎨 **Black** 24.3.0: Formatação (line-length=120)
- 📦 **isort** 5.13.2: Organização de imports (black profile)
- 🔍 **Flake8** 7.0.0: Linting (max-line-length=120)

## 📊 Métricas para Produção

Se tivesse mais tempo, adicionaria:

```python
# 1. Logging estruturado
logger.info("payment_captured", extra={
    "payment_id": payment.payment_id,
    "gross_amount": str(payment.gross_amount),
    "fee_percent": str(fee_percent),
    "split_count": len(receivables),
    "execution_time_ms": elapsed,
})

# 2. Métricas (Prometheus)
payments_total.labels(method="card", installments=3).inc()
payment_duration.observe(elapsed_ms)

# 3. Alertas
- Taxa de erro > 1% em 5 min
- Latência p99 > 500ms
- Divergências no ledger (sum != net)
- Conflitos de idempotência > threshold

# 4. Dashboards (Grafana)
- Payments por método e dia
- Taxa média por método
- Split distribution
- Idempotency hit rate

# 5. Queries de auditoria
SELECT SUM(amount) as total, COUNT(*) as count
FROM api_ledgerentry
WHERE payment_id = ?;
```

## 🤖 Como usei IA (Claude)

**Usadas para**:
- Rascunho da lógica core do SplitCalculator
- Listar edge cases de arredondamento
- Estrutura e padrão de testes
- Documentação técnica
- Debug de erros (Decimal JSON, ALLOWED_HOSTS)
- Infraestrutura (Dockerfile, docker-compose, GitHub Actions)
- Validações de negócio

**NÃO usei IA para** (decisões próprias):
- Arquitetura geral (Decimal, ROUND_DOWN, absorção)
- Choice de stack (Django + DRF)
- Estratégia de idempotência (conceito financeiro)
- Outbox Pattern (padrão de produção)
- Tabela de taxas e regras de negócio

## 📂 Estrutura do Projeto

```
cakto-mini-split-engine/
├── README.md                          ← documentação
├── requirements.txt                   ← dependências Python
├── manage.py                          ← CLI Django
├── Makefile                           ← comandos do projeto
├── docker-compose.dev.yml             ← composição local
├── Dockerfile.dev                     ← imagem desenvolvimento
├── .github/workflows/
│   ├── devtests.yml                   ← Testes em PR para develop
│   ├── deploystag.yml                 ← Deploy após merge em develop
│   └── deployprod.yml                 ← Deploy após merge em main
├── .pre-commit-config.yaml            ← code quality hooks
├── configs/
│   ├── settings.py                    ← Django settings
│   ├── urls.py                        ← URL routing
│   ├── wsgi.py
│   └── asgi.py
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── models.py                  ← Payment, LedgerEntry, OutboxEvent
│   │   ├── views.py                   ← PaymentCreateView
│   │   ├── serializers.py             ← PaymentRequestSerializer
│   │   ├── urls.py                    ← routing
│   │   ├── apps.py
│   │   ├── admin.py
│   │   ├── migrations/                ← Django DB migrations
│   │   └── tests/
│   │       ├── test_split_calculator.py
│   │       ├── test_views.py
│   │       ├── test_edge_cases.py
│   │       └── __init__.py
│   └── services/
│       └── split_calculator.py        ← Motor de cálculo
└── venv/                              ← Python venv
```

## 🌳 Branches Strategy

- **`main`**: Production. Protegida. Merge apenas via PR com testes passando.
- **`develop`**: Staging. Merge apenas via PR com devtests passando.
- **`feature/*`**: Features. Branch off de develop, PR contra develop.
  ```bash
  git checkout develop
  git pull origin develop
  git checkout -b feature/nova-feature
  # ... trabalho ...
  git push origin feature/nova-feature
  # Criar PR contra develop
  ```

## 🏁 Quick Start

```bash
# 1. Clonar
git clone <seu-repo>
cd cakto-mini-split-engine

# 2. Iniciar Docker (instala DC v2 se needed)
make dev

# 3. Rodar migrações
make migrate

# 4. Testar
make test

# 5. Fazer uma requisição
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: teste-123" \
  -d '{"amount":"100","currency":"BRL","payment_method":"pix","installments":1,"splits":[{"recipient_id":"p1","role":"producer","percent":100}]}'
```

---

**Stack**: Django 4.2 + DRF 3.14 + PostgreSQL 15 + Docker  
**Desenvolvido**: 2026 para Cakto  
**Status**: ✅ Pronto para produção