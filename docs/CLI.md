# MESHC(1) - Mesh Connect CLI Reference

## NAME

**meshc** - CLI for Mesh Connect deposit and payment flows

## SYNOPSIS

```
meshc [-v|--verbose] [--debug] [--json] COMMAND [OPTIONS]
```

## DESCRIPTION

**meshc** is a command-line interface for the Mesh Connect API. It enables creating link tokens for crypto deposits and payments, managing stored integration tokens, and testing flows in sandbox mode.

## GLOBAL OPTIONS

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable verbose output (INFO level logging) |
| `--debug` | Enable debug output (DEBUG level logging) |
| `--json` | Output results in JSON format |

---

## COMMANDS

### link-token

Create a Mesh link token for deposit or payment flows.

```
meshc link-token --user-id USER --address ADDR --symbol SYM [OPTIONS]
```

**Required Options:**

| Option | Description |
|--------|-------------|
| `--user-id USER` | Your application's user identifier |
| `--address ADDR` | Destination wallet address |
| `--symbol SYM` | Token symbol (e.g., USDC, XLM, EURC) |

**Optional Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--amount FLOAT` | - | Transfer amount |
| `--network-id ID` | Stellar | Blockchain network UUID |
| `--transfer-type TYPE` | deposit | Transfer type: `deposit` or `payment` |
| `--transaction-id ID` | - | Your transaction ID for reconciliation |
| `--integration-id ID` | - | Skip catalog, go directly to specific exchange |
| `--client-fee FLOAT` | - | Your fee as decimal (e.g., 0.025 = 2.5%) |
| `--amount-in-fiat FLOAT` | - | Amount in USD (auto-converts to crypto) |
| `--inclusive-fee` | false | Include fee in displayed amount |
| `--use-stored-tokens` | false | Use stored MMT tokens to skip re-auth |
| `--smart-funding` | true | Enable SmartFunding (auto-convert assets) |
| `--no-smart-funding` | - | Disable SmartFunding |
| `--json` | false | Output full response as JSON |

**Example:**

```bash
meshc link-token \
  --user-id user123 \
  --address GBXY...Q5NX \
  --symbol USDC \
  --amount 100 \
  --transfer-type deposit \
  --client-fee 0.01
```

---

### status

Check the status of a transfer by transaction ID.

```
meshc status TRANSACTION_ID [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `TRANSACTION_ID` | The transaction ID to check |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--poll` | false | Poll continuously until transfer completes |
| `--interval FLOAT` | 5.0 | Poll interval in seconds |
| `--json` | false | Output full response as JSON |

**Example:**

```bash
# Check status once
meshc status bpv1767777617849

# Poll until complete
meshc status bpv1767777617849 --poll --interval 3
```

---

### networks

List supported blockchain networks and their tokens.

```
meshc networks [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--filter NAME` | Filter networks by name (case-insensitive) |
| `--json` | Output full response as JSON |

**Example:**

```bash
# List all networks
meshc networks

# Filter by name
meshc networks --filter stellar

# Get JSON output
meshc networks --json

# Get Stellar network ID (alternative to removed stellar-id command)
meshc networks --filter stellar --json
```

---

### mock-deposit

Simulate a complete deposit flow for testing (creates link token + simulates completion).

```
meshc mock-deposit --user-id USER --address ADDR --symbol SYM --amount AMT [OPTIONS]
```

**Required Options:**

| Option | Description |
|--------|-------------|
| `--user-id USER` | User identifier |
| `--address ADDR` | Destination wallet address |
| `--symbol SYM` | Token symbol |
| `--amount FLOAT` | Transfer amount |

**Optional Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--network-id ID` | Stellar | Network UUID |
| `--delay FLOAT` | 2.0 | Simulated processing delay in seconds |
| `--json` | false | Output as JSON |

**Example:**

```bash
meshc mock-deposit \
  --user-id test-user \
  --address GBXY...Q5NX \
  --symbol USDC \
  --amount 50
```

---

### sandbox-cex

Test CEX (centralized exchange) flow in sandbox mode. Uses mocked exchange data.

```
meshc sandbox-cex [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--user-id USER` | test-user | User identifier |
| `--address ADDR` | (test Stellar addr) | Destination address |
| `--symbol SYM` | USDC | Token symbol |
| `--amount FLOAT` | - | Transfer amount |
| `--network-id ID` | Stellar | Network UUID |
| `--transfer-type TYPE` | deposit | `deposit` or `payment` |
| `--transaction-id ID` | (auto-generated) | Your transaction ID |
| `--client-fee FLOAT` | - | Your fee as decimal |
| `--smart-funding` | true | Enable SmartFunding |
| `--no-smart-funding` | - | Disable SmartFunding |
| `--lang CODE` | - | UI language (en, fr, es, de, ja) |
| `--wallet` | false | Use wallet mode (Sepolia testnet) |
| `--instructions` | false | Show testing instructions |
| `--open` | false | Auto-open URL in browser |
| `--json` | false | Output as JSON |

**Example (CEX mode):**

```bash
# Quick CEX test with browser
meshc sandbox-cex --open

# CEX with custom configuration
meshc sandbox-cex \
  --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX \
  --symbol USDC \
  --amount 100 \
  --open
```

**Example (Wallet mode):**

```bash
# Wallet test on Sepolia testnet
meshc sandbox-cex --wallet --address 0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c --open
```

**Test Accounts:**

| Network | Address |
|---------|---------|
| Stellar testnet | `GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX` |
| Sepolia testnet | `0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c` |

**Sepolia Faucet:** https://cloud.google.com/application/web3/faucet/ethereum/sepolia

**Testing Credentials (CEX mode):**

In sandbox mode, use any credentials to authenticate:
- Username: `MeshUser` (or any)
- Password: `rPpass123` (or any)

---

### errors

List known Mesh API error codes and descriptions.

```
meshc errors [CODE]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `CODE` | (Optional) Specific error code to look up |

**Example:**

```bash
# List all error codes
meshc errors

# Look up specific code
meshc errors INSUFFICIENT_BALANCE
```

---

### token-store

Store an integration token for reuse (Mesh Managed Tokens / MMT).

```
meshc token-store --token-id ID --integration-type TYPE [OPTIONS]
```

**Required Options:**

| Option | Description |
|--------|-------------|
| `--token-id ID` | Mesh-provided token ID |
| `--integration-type TYPE` | Integration type (Coinbase, Binance, MetaMask, etc.) |

**Optional Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--user-id USER` | - | User identifier |
| `--wallet-address ADDR` | - | Wallet public key |
| `--scope SCOPE` | read | Token scope: `read` or `write` |
| `--lang CODE` | en | Language code (en, fr, es, de, ja) |
| `--expires-at TS` | - | Expiration timestamp (ISO 8601) |
| `--metadata JSON` | - | Additional metadata as JSON string |
| `--json` | false | Output as JSON |

**Example:**

```bash
meshc token-store \
  --token-id abc123... \
  --integration-type Coinbase \
  --user-id user123 \
  --scope write
```

---

### token-list

List stored integration tokens.

```
meshc token-list [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--user-id USER` | Filter by user ID |
| `--wallet-address ADDR` | Filter by wallet address |
| `--integration-type TYPE` | Filter by integration type |
| `--active-only` | Only show active (non-revoked) tokens |
| `--json` | Output as JSON |

**Example:**

```bash
# List all tokens
meshc token-list

# Filter by user
meshc token-list --user-id user123 --active-only
```

---

### token-get

Get details of a specific stored token.

```
meshc token-get TOKEN_ID [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `TOKEN_ID` | The token ID to retrieve |

**Options:**

| Option | Description |
|--------|-------------|
| `--integration-type TYPE` | Filter by integration type |
| `--json` | Output as JSON |

**Example:**

```bash
meshc token-get abc123...
```

---

### token-revoke

Revoke a stored token.

```
meshc token-revoke TOKEN_ID [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `TOKEN_ID` | The token ID to revoke |

**Options:**

| Option | Description |
|--------|-------------|
| `--integration-type TYPE` | Filter by integration type |

**Example:**

```bash
meshc token-revoke abc123...
```

---

## CONFIGURATION

Credentials are loaded in this priority order:

1. **Environment variables:**
   - `MESH_CLIENT_ID`
   - `MESH_SECRET`
   - `MESH_API` (API base URL)

2. **local_settings.py** in current directory:
   ```python
   MESH_CLIENT_ID = "your-client-id"
   MESH_SECRET = "your-secret"
   MESH_API = "https://sandbox-integration-api.meshconnect.com"
   ```

3. **Defaults:**
   - API URL: `https://sandbox-integration-api.meshconnect.com`

**Token Storage:**

Stored tokens are saved to `~/.meshc/tokens.db` (SQLite database).

---

## EXAMPLES

**Complete deposit flow:**

```bash
# 1. Create a link token
TOKEN=$(meshc link-token \
  --user-id user123 \
  --address GBXY...Q5NX \
  --symbol USDC \
  --amount 100 \
  --transaction-id tx-001)

# 2. User completes flow in browser using the token URL

# 3. Check status
meshc status tx-001 --poll
```

**Sandbox testing:**

```bash
# Test exchange flow
meshc sandbox-cex --open

# Test wallet flow (requires Sepolia ETH)
meshc sandbox-wallet --address 0x1234... --open
```

**Token management (MMT):**

```bash
# Store a token received from webhook
meshc token-store \
  --token-id tok_abc123 \
  --integration-type Coinbase \
  --user-id user123

# Use stored tokens for faster re-auth
meshc link-token \
  --user-id user123 \
  --address GBXY... \
  --symbol USDC \
  --use-stored-tokens
```

---

## EXIT CODES

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Error (API error, configuration error, etc.) |
| 2 | No command specified |

---

## SEE ALSO

- Mesh Connect API Documentation: https://docs.meshconnect.com
- GitHub Repository: https://github.com/anthropics/meshc

---

## VERSION

meshc 0.1.0
