# meshc

CLI and library for Mesh Connect deposit flows.

## Install

```bash
uv pip install -e .
```

## Configure

Create `local_settings.py`:

```python
MESH_CLIENT_ID = "your-client-id"
MESH_SECRET = "your-secret"
```

Or use environment variables:

```bash
export MESH_CLIENT_ID="..."
export MESH_SECRET="..."
```

## CLI Usage

```bash
# List networks
meshc networks

# Create link token
meshc link-token --user-id user123 --address GADDR... --symbol USDC

# Simulate deposit
meshc mock-deposit --user-id user123 --address GADDR... --symbol USDC --amount 100
```

## Library Usage

```python
from meshc import create_link_token, ToAddress, load_config

config = load_config()
result = create_link_token(
    client_id=config["client_id"],
    client_secret=config["client_secret"],
    user_id="user123",
    to_addresses=[ToAddress(symbol="USDC", address="G...", network_id="...")],
)
print(result.token)
```

## Mesh Managed Tokens (MMT)

Mesh Managed Tokens allow you to **store and reuse integration tokens** so users don't have to re-authenticate with their exchange or wallet every time. Once a user connects their Coinbase account, you can store that token and automatically use it in future sessions.

### Why Use MMT?

- **Skip re-authentication**: Users authenticate once, reuse tokens indefinitely
- **Better UX**: No repeated OAuth flows for returning users
- **Persistent sessions**: Tokens survive across app restarts
- **Multi-integration support**: Store tokens for multiple exchanges per user

### Configuration

Token storage database path (default: `~/.meshc/tokens.db`):

```python
# local_settings.py
MESHC_TOKEN_DB = "/path/to/tokens.db"
```

Or via environment variable:

```bash
export MESHC_TOKEN_DB="/path/to/tokens.db"
```

### CLI Usage

#### Store a Token

After a user completes the Mesh Link flow, store their integration token:

```bash
meshc token-store \
  --token-id tok_abc123... \
  --integration-type Coinbase \
  --user-id user123 \
  --scope read \
  --lang en
```

For wallet integrations, use `--wallet-address` instead of `--user-id`:

```bash
meshc token-store \
  --token-id tok_xyz789... \
  --integration-type MetaMask \
  --wallet-address 0x1234567890abcdef \
  --scope write \
  --lang fr
```

#### List Stored Tokens

```bash
# List all tokens
meshc token-list

# Filter by user
meshc token-list --user-id user123

# Filter by integration type
meshc token-list --integration-type Coinbase

# Show only active tokens
meshc token-list --active-only

# JSON output
meshc token-list --user-id user123 --json
```

#### Get Token Details

```bash
# Get specific token
meshc token-get tok_abc123

# Filter by integration type
meshc token-get tok_abc123 --integration-type Coinbase
```

#### Revoke a Token

```bash
# Soft delete (keeps for audit trail)
meshc token-revoke tok_abc123
```

#### Use Stored Tokens

When creating a link token, automatically include stored tokens:

```bash
meshc link-token \
  --user-id user123 \
  --address GADDR... \
  --symbol USDC \
  --use-stored-tokens
```

This skips the authentication UI for exchanges where the user already has stored tokens.

### Library Usage

#### Store Tokens from Frontend Callback

When your frontend receives the `integrationConnected` event from Mesh Link:

```python
from meshc import store_token

# From your webhook or frontend callback
def handle_integration_connected(data):
    """Store token when user completes Mesh Link flow."""
    token_id = data["tokenId"]
    integration_type = data["type"]  # "Coinbase", "Binance", etc.
    user_id = data.get("userId")  # Your app's user ID
    user_lang = data.get("lang", "en")  # User's preferred language

    store_token(
        token_id=token_id,
        integration_type=integration_type,
        user_id=user_id,
        scope="read",  # or "write" for transfers
        lang=user_lang,  # Store user language preference
    )
```

For wallet integrations:

```python
# Wallet connection
store_token(
    token_id=token_id,
    integration_type="MetaMask",
    wallet_address="0x...",
    scope="write",
    lang="fr",  # User's language preference
)
```

#### Retrieve and Use Tokens

Automatically load stored tokens when creating link tokens:

```python
from meshc import create_link_token, get_account_tokens_for_user, ToAddress, load_config

config = load_config()

# Get stored tokens for user
account_tokens = get_account_tokens_for_user(user_id="user123")

# Create link token with stored tokens (skip re-auth)
result = create_link_token(
    client_id=config["client_id"],
    client_secret=config["client_secret"],
    user_id="user123",
    to_addresses=[ToAddress(symbol="USDC", address="G...", network_id="...")],
    account_tokens=account_tokens,  # User won't see auth UI for these
)
```

#### List Tokens with Filters

```python
from meshc import list_tokens

# List all active tokens for a user
tokens = list_tokens(user_id="user123", active_only=True)

for token in tokens:
    print(f"{token.integration_type}: {token.token_id}")
    print(f"  Status: {token.status}")
    print(f"  Created: {token.created_at}")
```

#### Revoke Tokens

```python
from meshc import revoke_token

# Soft delete (audit trail preserved)
success = revoke_token("tok_abc123")

if success:
    print("Token revoked")
```

#### Complete Workflow Example

```python
from meshc import (
    create_link_token,
    get_account_tokens_for_user,
    store_token,
    ToAddress,
    load_config,
)

config = load_config()

# Step 1: Check for existing tokens
account_tokens = get_account_tokens_for_user(user_id="user123")

# Step 2: Create link token (with or without stored tokens)
result = create_link_token(
    client_id=config["client_id"],
    client_secret=config["client_secret"],
    user_id="user123",
    to_addresses=[ToAddress(symbol="USDC", address="G...", network_id="...")],
    account_tokens=account_tokens if account_tokens else None,
)

print(f"Link token: {result.token}")

# Step 3: After user completes flow, store new token
# (This would come from your webhook/frontend callback)
def on_integration_connected(token_id, integration_type):
    store_token(
        token_id=token_id,
        integration_type=integration_type,
        user_id="user123",
        scope="read",
    )
    print(f"Stored {integration_type} token for future use")
```

### Token Storage Schema

Tokens are stored in SQLite with the following fields:

- `token_id` - Mesh token ID
- `integration_type` - Integration name (Coinbase, Binance, MetaMask, etc.)
- `user_id` - Your application's user identifier (nullable)
- `wallet_address` - Wallet public key for wallet integrations (nullable)
- `scope` - Token scope: `read` or `write` (default: `read`)
- `status` - Token status: `active`, `revoked`, or `expired` (default: `active`)
- `lang` - User language code: `en`, `fr`, `es`, etc. (default: `en`, indexed)
- `created_at` / `updated_at` - Timestamps
- `expires_at` - Optional expiration timestamp
- `metadata` - JSON field for additional data

**Note for existing users**: If you have an existing token database from before the `lang` field was added, delete `~/.meshc/tokens.db` (or your custom path) to recreate the database with the updated schema.

### Security Notes

- Tokens are stored in plain SQLite (database file has 0600 permissions)
- Default location: `~/.meshc/tokens.db` (hidden directory)
- Use `revoke_token()` for soft delete (preserves audit trail)
- Consider encrypting `token_id` field in production
- Tokens should be treated as sensitive credentials
