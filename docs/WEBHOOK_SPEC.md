# Django Webhook Endpoint Specification

## Overview

The `meshsbox` Django app receives Mesh Connect webhook events. One record per `transaction_id`, with multiple webhooks appending to a history log.

**Endpoint**: `POST /meshc/api/webhook/`

---

## Model: MeshWebhook

**Table**: `meshsbox_webhook`

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | CharField(64) | Primary identifier from Mesh, unique |
| `status` | CharField(32) | Latest status: Pending, Succeeded, Failed |
| `destination_address` | CharField(128) | Target wallet address |
| `token` | CharField(16) | USDC, ETH, etc. |
| `chain` | CharField(32) | Stellar, Ethereum |
| `source_provider` | CharField(32) | Coinbase, Binance |
| `amount` | Decimal(20,8) | Transfer amount |
| `tx_hash` | CharField(128) | Blockchain transaction hash |
| `history` | JSONField | Array of complete webhook payloads (append-only) |
| `created_at` | DateTime | First webhook received |
| `updated_at` | DateTime | Last webhook received |

---

## IP Allowlist

**Setting**: `WEBHOOK_ALLOWED_IPS`

```python
# Default: localhost (dev) + Mesh production IP
WEBHOOK_ALLOWED_IPS = ['127.0.0.1', '20.22.113.37']
```

**Override via environment**:
```bash
# Production only (disable localhost)
WEBHOOK_ALLOWED_IPS=20.22.113.37 python manage.py runserver
```

---

## Behavior

1. **First webhook** for a `transaction_id` → Creates new record
2. **Subsequent webhooks** → Appends payload to `history`, updates `status`, `tx_hash`

### Response Codes

| Code | Condition |
|------|-----------|
| 200 | Success: `{"status": "ok", "transaction_id": "..."}` |
| 400 | Invalid JSON, missing TransactionId or TransferStatus |
| 403 | IP not in allowlist |
| 405 | Method not allowed (GET) |

---

## Webhook Payload Reference

From Mesh (fields extracted):
```json
{
  "TransactionId": "bpv1720532648123",
  "TransferStatus": "Pending|Succeeded|Failed",
  "DestinationAddress": "GBXY...",
  "Token": "USDC",
  "Chain": "Stellar",
  "SourceAccountProvider": "Coinbase",
  "SourceAmount": 50.0,
  "TxHash": "abc123..."
}
```

Full payload stored in `history` array for audit trail.

---

## Files

| File | Purpose |
|------|---------|
| `meshsbox/models.py` | MeshWebhook model |
| `meshsbox/views.py` | api_webhook view with IP filter |
| `meshsbox/urls.py` | URL routing |
| `meshsbox/admin.py` | Admin interface |
| `meshc_django/settings.py` | WEBHOOK_ALLOWED_IPS setting |

---

## Testing

```bash
# Run migrations
python manage.py migrate meshsbox

# Deploy (runs on port 10409)
./deploy.sh

# Test against dev server (default)
curl -X POST https://meshcdev.bpventures.us/meshc/api/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"TransactionId": "test123", "TransferStatus": "Pending", "Token": "USDC"}'

# Or test locally (port 10409 from deploy.sh)
curl -X POST http://localhost:10409/meshc/api/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"TransactionId": "test123", "TransferStatus": "Pending", "Token": "USDC"}'

# Using mock_webhook.py
python scripts/mock_webhook.py --status Pending --webhook-url https://meshcdev.bpventures.us/meshc/api/webhook/
python scripts/mock_webhook.py --status Succeeded --webhook-url https://meshcdev.bpventures.us/meshc/api/webhook/

# Run unit tests
python manage.py test meshsbox

# Admin
# https://meshcdev.bpventures.us/admin/meshsbox/meshwebhook/
# Local: http://localhost:10409/admin/meshsbox/meshwebhook/
```
