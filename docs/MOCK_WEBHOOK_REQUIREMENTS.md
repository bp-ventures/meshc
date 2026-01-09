# Mock Webhook Script Requirements

## Overview

A Python script to generate and send mock Mesh webhook payloads for testing. The script simulates webhooks that Mesh would send after a transfer completes, using data from the same CLI arguments as `sandbox-cex`.

## Purpose

- Test webhook handling without completing full transfer flows
- Simulate different transfer statuses (Pending, Succeeded, Failed)
- Verify webhook endpoint integration
- Speed up development iteration

## Webhook Payload Structure

Based on actual Mesh webhook format:

```json
{
  "Id": "358c6ab7-4518-416b-9266-c680fda3a8dd",
  "EventId": "56713e70-be74-4a37-0036-08da97f5941a",
  "SentTimestamp": 1720532648,
  "UserId": "user_id_provided_by_client",
  "TransactionId": "transaction_id_provided_by_client",
  "TransferId": "dd4063e5-f317-441c-3f07-08dc7353b6f8",
  "TransferStatus": "Pending",
  "TxHash": "0x7d4ec1ce50952a377452c95fdf5a787ff551f08c0343093f866c84f57c473495",
  "Chain": "Ethereum",
  "Token": "ETH",
  "DestinationAddress": "0x0Ff0000f0A0f0000F0F000000000ffFf00f0F0f0",
  "SourceAccountProvider": "Binance",
  "SourceAmount": 0.004786046226555188,
  "DestinationAmount": 0.004786046226555188,
  "RefundAddress": "0x0Ff0000f0A0f0000F0F000000000ffFf00f0F0f0",
  "Timestamp": 1715175519038
}
```

## Field Mapping from CLI Arguments

| Webhook Field | CLI Source | Default Value | Notes |
|---------------|------------|---------------|-------|
| `Id` | Auto-generate | UUID | Unique webhook event ID |
| `EventId` | Auto-generate | UUID | Unique event ID |
| `SentTimestamp` | Auto-generate | `time.time()` | Unix seconds |
| `UserId` | `--user-id` | "test-user" | From sandbox-cex |
| `TransactionId` | `--transaction-id` | "bpv{ts}{rand}" | Auto-generate if not provided |
| `TransferId` | Auto-generate | UUID | Unique transfer ID |
| `TransferStatus` | `--status` | "Succeeded" | New arg |
| `TxHash` | Auto-generate | Chain-specific | `0x...` for ETH, hex for Stellar |
| `Chain` | Derived | From network-id | Map network ID to chain name |
| `Token` | `--symbol` | "USDC" | From sandbox-cex |
| `DestinationAddress` | `--address` | Stellar test addr | From sandbox-cex |
| `SourceAccountProvider` | `--provider` | "Coinbase" | New arg |
| `SourceAmount` | `--amount` | 50.0 | From sandbox-cex |
| `DestinationAmount` | `--amount` | Same as source | No fee deduction in mock |
| `RefundAddress` | Same as address | - | For CEX flows |
| `Timestamp` | Auto-generate | `time.time() * 1000` | Unix milliseconds |

## Network ID to Chain Mapping

| Network ID | Chain Name |
|------------|------------|
| `06855704-43d2-4ad2-a73c-372f0c3534e1` | Stellar |
| `03b2d786-7092-4a6a-9737-d6013e21819b` | Ethereum (Sepolia) |

Unknown network IDs should log a warning and use "Unknown" as chain name.

## CLI Arguments

### From sandbox-cex (reused)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--user-id` | string | "test-user" | User identifier |
| `--address` | string | Test Stellar addr | Destination address |
| `--symbol` | string | "USDC" | Token symbol |
| `--amount` | float | 50.0 | Transfer amount |
| `--network-id` | string | Stellar network ID | Network identifier |
| `--transaction-id` | string | Auto-generated | Your transaction ID |

### New webhook-specific

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--status` | choice | "Succeeded" | TransferStatus: Pending, Succeeded, Failed |
| `--provider` | string | "Coinbase" | Source exchange (Coinbase, Binance, etc.) |
| `--webhook-url` | string | From settings | Override MESH_WEBHOOK_URL |
| `--dry-run` | flag | false | Print payload without sending |

## Configuration

The script reads `MESH_WEBHOOK_URL` from `local_settings.py`:

```python
# local_settings.py
MESH_WEBHOOK_URL = "https://webhook.site/your-unique-id"
```

Can be overridden with `--webhook-url` argument.

## Usage Examples

```bash
# Basic usage - send Succeeded webhook with defaults
python scripts/mock_webhook.py

# Preview payload without sending
python scripts/mock_webhook.py --dry-run

# Simulate a failed transfer
python scripts/mock_webhook.py --status Failed

# Simulate pending from Binance
python scripts/mock_webhook.py --status Pending --provider Binance

# Custom transfer details
python scripts/mock_webhook.py \
    --user-id my-user-123 \
    --amount 100.0 \
    --symbol ETH \
    --network-id 03b2d786-7092-4a6a-9737-d6013e21819b

# Override webhook URL
python scripts/mock_webhook.py --webhook-url https://my-server.com/webhook
```

## Expected Output

```
Webhook Payload:
============================================================
{
  "Id": "358c6ab7-4518-416b-9266-c680fda3a8dd",
  "EventId": "56713e70-be74-4a37-0036-08da97f5941a",
  "SentTimestamp": 1720532648,
  "UserId": "test-user",
  "TransactionId": "bpv1720532648123",
  ...
}

Sending to: https://webhook.site/cf69e8e5-2235-4248-a3ae-b3fc9da3685d

Success: HTTP 200
```

## Dependencies

- `httpx` - HTTP client (already a project dependency)
- `meshc.config` - For loading local_settings.py and network ID constants

## File Location

`scripts/mock_webhook.py`
