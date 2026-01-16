# Withdraw Template: Wallet → Exchange Flow

## Overview

The withdraw template enables **Wallet → Exchange** transfers using the Mesh SDK. This is the reverse of the deposit flow (Exchange → Wallet).

| Flow | Direction | Example |
|------|-----------|---------|
| **Deposit** | Exchange → Your App | User withdraws from Coinbase → funds arrive at your Stellar address |
| **Withdraw** | Wallet → Exchange | User connects MetaMask → funds transfer to their Coinbase deposit address |

---

## Routes

| Route | Method | Handler | Purpose |
|-------|--------|---------|---------|
| `/meshc/withdraw/` | GET | `withdraw()` | Renders the withdraw form |
| `/meshc/api/withdraw-token/` | POST | `api_withdraw_token()` | Generates link token for withdrawal |

---

## Architecture

```
User loads /meshc/withdraw/
         ↓
Browser renders withdraw form (withdraw.html)
         ↓
User fills form (user_id, exchange, symbol, amount)
         ↓
User clicks "Withdraw to Exchange"
         ↓
JS submits to POST /meshc/api/withdraw-token/
         ↓
View looks up stored IntegrationToken (from previous deposit)
         ↓
View calls get_exchange_deposit_address() → fetches user's exchange deposit address
         ↓
View calls create_link_token() with toAddresses = exchange deposit address
         ↓
View returns {link_token, deposit_address, chain, expires_at}
         ↓
JS imports @meshconnect/web-link-sdk
         ↓
JS calls link.openLink(link_token)
         ↓
Mesh modal opens (user connects wallet: MetaMask, Rainbow, etc.)
         ↓
User confirms transfer from wallet to exchange
         ↓
SDK fires onTransferFinished(result)
         ↓
JS displays result JSON
```

---

## Prerequisite: Stored Auth Token

The withdraw flow **requires** that the user has previously completed a deposit with "Easy Relogin" enabled. This stores their `IntegrationToken` in the database:

- `token_id`: The Mesh auth token for their exchange connection
- `integration_type`: "Coinbase", "Binance", etc.
- `user_id`: Their identifier (Stellar/Ethereum address)

If no stored token exists, the API returns an error prompting the user to complete a deposit first.

---

## API Endpoint

### `POST /meshc/api/withdraw-token/`

**Request:**
```json
{
  "user_id": "GBXYIBA4JX4BMI...",
  "exchange": "coinbase",
  "symbol": "ETH",
  "amount": 0.1
}
```

**Response (success):**
```json
{
  "link_token": "mesh_link_...",
  "deposit_address": "0x1234...",
  "chain": "ETH",
  "expires_at": "2026-01-16T..."
}
```

**Response (no stored token):**
```json
{
  "error": "No stored Coinbase connection found. Please complete a deposit with \"Easy Relogin\" enabled first."
}
```

---

## Core Library Addition

### `get_exchange_deposit_address()`

New function in `src/meshc/core.py` that fetches a user's exchange deposit address:

```python
def get_exchange_deposit_address(
    client_id: str,
    client_secret: str,
    auth_token: str,
    symbol: str,
    network_id: str,
    exchange_type: str,  # "coinbase", "binanceInternational"
    api_url: str = SANDBOX_API_URL,
) -> ExchangeDepositAddress:
    """Fetch user's exchange deposit address for withdrawals.

    Calls: POST /api/v1/transfers/managed/address/get
    Returns: ExchangeDepositAddress(symbol, address, chain)
    """
```

### `ExchangeDepositAddress` dataclass

```python
@dataclass
class ExchangeDepositAddress:
    symbol: str   # Token symbol (e.g., "ETH", "USDC")
    address: str  # Deposit address on the exchange
    chain: str    # Network/chain name (e.g., "ETH", "DOGE")
    raw: dict     # Full API response
```

---

## Configuration

### Exchange Type Mapping

| UI Name | Mesh API `type` Parameter |
|---------|---------------------------|
| Coinbase | `coinbase` |
| Binance | `binanceInternational` |

### Network ID Mapping

| Symbol | Network ID |
|--------|------------|
| ETH | `e3c7fdd8-b1fc-4e51-85ae-bb276e075611` |
| USDC | `e3c7fdd8-b1fc-4e51-85ae-bb276e075611` |
| XLM | `06855704-43d2-4ad2-a73c-372f0c3534e1` |

---

## Error Handling

| Error | Message |
|-------|---------|
| No stored token | "No stored {Exchange} connection found. Please complete a deposit with 'Easy Relogin' enabled first." |
| Expired token | "Your exchange connection has expired. Please reconnect via a new deposit." |
| Unsupported symbol | "Unsupported symbol: {symbol}" |
| Missing fields | "{field} is required" |

---

## Files

| File | Purpose |
|------|---------|
| `meshsbox/templates/meshsbox/withdraw.html` | Withdraw form UI (pink gradient theme) |
| `meshsbox/templates/meshsbox/link.html` | Deposit form with nav link to withdraw |
| `meshsbox/views.py` | `withdraw()` and `api_withdraw_token()` handlers |
| `meshsbox/urls.py` | Route definitions |
| `src/meshc/core.py` | `get_exchange_deposit_address()` and `ExchangeDepositAddress` |
| `src/meshc/__init__.py` | Package exports |

---

## Testing

### Manual E2E Test

1. Start Django server:
   ```bash
   cd meshc_django && python manage.py runserver
   ```

2. Complete deposit flow at `/meshc/` with "Easy Relogin" checked

3. Navigate to `/meshc/withdraw/` (or click "Switch to Withdraw →")

4. Fill form:
   - User ID: same as deposit
   - Exchange: Coinbase or Binance
   - Symbol: ETH or USDC
   - Amount: optional

5. Click "Withdraw to Exchange"

6. In Mesh Link UI:
   - Connect wallet (MetaMask)
   - Confirm transfer

7. Verify result JSON shows transfer status
