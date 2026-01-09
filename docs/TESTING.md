# Mesh Deposit Testing Guide

A step-by-step guide to test the Mesh deposit flow end-to-end.

---

## What is Mesh?

Mesh is a crypto payments network that lets users transfer assets from exchanges (Coinbase, Binance) or wallets (MetaMask) to your application—without leaving your app. You embed a "Link UI" that handles authentication and transfers.

**The flow:**
1. Your backend creates a "link token" (API call)
2. Your frontend opens the Mesh Link UI with that token
3. User logs into their exchange/wallet and approves the transfer
4. Mesh moves the funds and sends you a webhook

---

## Prerequisites

```bash
# 1. Install the CLI
cd /path/to/meshc
uv venv && source .venv/bin/activate
uv pip install -e .

# 2. Configure credentials (already done if you have local_settings.py)
cat local_settings.py
# Should show: MESH_CLIENT_ID, MESH_SECRET, MESH_API
```

---

## Test 1: Exchange Flow (Mocked Data)

This tests the flow where a user transfers from Coinbase/Binance. In sandbox mode, everything is simulated—no real money moves.

### Step 1: Generate and Open Link

```bash
meshc sandbox-cex --open
```

This command:
1. **Generates** a link token from Mesh API
2. **Decodes** the base64 token to get the actual URL
3. **Opens** the URL automatically in your browser

Output:
```
SANDBOX CEX TEST
========================================
Link URL: https://sandbox-web.meshconnect.com/b2b-iframe/358ef0a7-.../broker-connect?auth_code=...

Next steps:
1. Select any exchange (Coinbase, Binance, etc.)
2. Use credentials Displayed (e.g., user123/pass123)
3. Complete the mocked transfer flow

Opening in browser...
```

**Without --open flag**: The URL is still displayed, but you need to manually copy/paste it into your browser:

```bash
meshc sandbox-cex
# Output includes: Link URL: https://...
# Copy the URL and paste into browser
```

### Step 2: Complete the Mock Flow

1. **Select an exchange** → Click "Coinbase" (or any exchange)
2. **Enter credentials** → Use ANY username/password (e.g., `user123` / `pass123`)
3. **Select asset** → Choose USDC or any listed asset
4. **Confirm transfer** → Click through the confirmation screens

The transfer will "succeed" with mock data.

### Step 3: Verify with Webhook.site

Use [webhook.site](https://webhook.site) to receive and inspect webhooks without setting up a server:

1. **Get a webhook URL:**
   - Go to: https://webhook.site
   - Copy your unique URL (e.g., `https://webhook.site/abc-123-xyz`)

2. **Configure in Mesh Dashboard:**
   - Go to: https://dashboard.meshconnect.com
   - Navigate to: Account → Settings → Webhooks
   - Add your webhook.site URL
   - Save

3. **Complete a transfer** (steps above)

4. **Check webhook.site:**
   - Refresh the webhook.site page
   - You'll see the `transfer.completed` event with full payload:
   ```json
   {
     "type": "transfer.completed",
     "data": {
       "status": "succeeded",
       "amount": "10.00",
       "symbol": "USDC",
       "transactionId": "...",
       "networkTransactionId": "0x..."
     }
   }
   ```

---

## Test 2: Wallet Flow (Real Testnet Transaction)

This tests the flow where a user transfers from MetaMask. Uses Sepolia testnet—real blockchain transaction, but no real money.

### Step 1: Get Sepolia Test ETH

You need free testnet ETH to pay gas fees:

1. Go to: https://cloud.google.com/application/web3/faucet/ethereum/sepolia
2. Enter your MetaMask wallet address
3. Click "Request" to receive ~0.05 Sepolia ETH

### Step 2: Generate and Open Link

```bash
# Use YOUR MetaMask address (the one with Sepolia ETH)
meshc sandbox-wallet --address 0xYOUR_METAMASK_ADDRESS --open
```

This command:
1. **Generates** a link token for Sepolia testnet
2. **Decodes** the URL automatically
3. **Opens** it in your browser

Output:
```
SANDBOX WALLET TEST (Sepolia Testnet)
========================================
Link URL: https://sandbox-web.meshconnect.com/b2b-iframe/...

Prerequisites:
1. Get Sepolia ETH: https://cloud.google.com/application/web3/faucet/ethereum/sepolia
2. Send to your MetaMask/Rainbow wallet

Next steps:
1. Select MetaMask or Rainbow
2. Approve the on-chain transaction
3. Verify at: https://sepolia.etherscan.io

Opening in browser...
```

**Without --open flag**: The URL is displayed but not opened automatically.

### Step 3: Connect MetaMask

1. **Select wallet** → Click "MetaMask"
2. **Connect** → MetaMask popup appears, approve connection
3. **Switch network** → If prompted, switch to Sepolia testnet
4. **Approve transaction** → MetaMask asks you to sign; confirm it

### Step 4: Verify on Block Explorer

After confirmation, check the transaction:

1. Go to: https://sepolia.etherscan.io
2. Search for your wallet address
3. See the outgoing transaction

---

## Quick Reference

| Command | What it does |
|---------|--------------|
| `meshc sandbox-cex` | Generate URL for exchange test (mocked) |
| `meshc sandbox-cex --open` | Generate and auto-open in browser |
| `meshc sandbox-cex --instructions` | Show CEX testing steps |
| `meshc sandbox-wallet --address 0x...` | Generate URL for wallet test (Sepolia) |
| `meshc sandbox-wallet --address 0x... --open` | Generate and auto-open in browser |
| `meshc sandbox-wallet --instructions` | Show wallet testing steps |
| `meshc networks` | List all supported networks |
| `meshc errors` | List all error codes |

---

## Decoding Link Tokens (Optional)

By default, `meshc` commands automatically decode and display the URL. If you're working with the JSON API output, you can decode manually:

```bash
# Get raw base64 token from JSON output
meshc sandbox-cex --json | python -c "import sys,json; print(json.load(sys.stdin)['linkToken'])"

# Decode it
echo "BASE64_TOKEN" | base64 -d

# Or in one command
meshc sandbox-cex --json | python -c "import sys,json,base64; print(base64.b64decode(json.load(sys.stdin)['linkToken']).decode())"
```

---

## Common Issues

### "Invalid address pattern"
Your address format doesn't match the network. Stellar addresses start with `G`, Ethereum with `0x`.

```bash
# Check what address pattern a network expects:
meshc networks --json | python -c "
import sys,json
for n in json.load(sys.stdin):
    print(f\"{n['name']}: {n.get('addressPattern', 'N/A')}\")
"
```

### "Network not found"
You're using an invalid network ID. List valid IDs:

```bash
meshc networks
```

### "Insufficient funds" (wallet test)
You need Sepolia ETH for gas. Get some from the faucet:
https://cloud.google.com/application/web3/faucet/ethereum/sepolia

### Link UI shows error
Check the browser console (F12 → Console) for details. Common causes:
- Expired token (tokens are short-lived)
- Wrong API URL (must use sandbox for testing)

---

## Setting Up Webhooks (Recommended)

Webhooks are how Mesh notifies you when a transfer completes. For testing, use webhook.site—no server required.

### Quick Setup with webhook.site

```bash
# 1. Open in browser and copy your unique URL:
#    https://webhook.site
#    → You'll get something like: https://webhook.site/abc-123-xyz

# 2. Add to Mesh Dashboard:
#    https://dashboard.meshconnect.com → Account → Settings → Webhooks
#    → Paste your webhook.site URL → Save

# 3. Run a test transfer:
meshc sandbox-cex

# 4. Complete the flow in browser, then check webhook.site for the event
```

### Webhook Event Types

| Event | When it fires |
|-------|---------------|
| `transfer.initiated` | User started a transfer |
| `transfer.completed` | Transfer succeeded or failed |
| `connection.created` | User connected an exchange/wallet |

### Example Webhook Payload

```json
{
  "type": "transfer.completed",
  "timestamp": "2025-01-06T12:00:00Z",
  "data": {
    "transactionId": "your-tx-id-123",
    "status": "succeeded",
    "amount": "100.00",
    "symbol": "USDC",
    "networkId": "06855704-43d2-4ad2-a73c-372f0c3534e1",
    "networkTransactionId": "0xabc123...",
    "fromAddress": "...",
    "toAddress": "GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX"
  }
}
```

### Verifying Webhooks in Production

In production, always verify webhook data by polling the Mesh API:

```bash
# After receiving webhook, confirm with API:
meshc status YOUR_TRANSACTION_ID --json
```

This protects against spoofed webhooks.

---

## Mesh Managed Tokens (MMT) Testing

Mesh Managed Tokens (MMT) let you store and reuse integration tokens across test sessions. Once a user authenticates with an exchange or wallet, you save that token and automatically use it in future tests—skipping the authentication UI.

### Why Use MMT in Testing?

- **Skip re-auth**: No need to log in every test
- **Faster iteration**: Complete flows in seconds, not minutes
- **Multiple integrations**: Test Coinbase + MetaMask in one flow
- **Token persistence**: Tokens survive across CLI restarts

### Quick Start: Store and Reuse a Token

#### Step 1: Complete a Sandbox Flow

First, run a sandbox test and complete the authentication:

```bash
meshc sandbox-cex
# (complete the flow in browser, login to Coinbase)
```

After completing the flow, you'll see the token ID in webhook or transfer status. For testing purposes, we'll use a mock token ID:

```bash
# Simulate storing a token from a completed flow
meshc token-store \
  --token-id "tok_test_coinbase_abc123" \
  --integration-type Coinbase \
  --user-id "test-user" \
  --scope read \
  --lang en
```

Output:
```
stored token: tok_test_coinbase... (Coinbase)
  user_id: test-user
  scope: read
  lang: en
  status: active
```

#### Step 2: Verify Token Storage

List all tokens for your test user:

```bash
meshc token-list --user-id test-user
```

Output:
```
Token ID                       Type            User/Wallet               Scope  Lang Status
===============================================================================================
tok_test_coinbase_abc12...     Coinbase        test-user                 read   en   active

Total: 1 token(s)
```

Or get details of a specific token:

```bash
meshc token-get tok_test_coinbase_abc123
```

Output:
```
Token ID: tok_test_coinbase_abc123
Integration: Coinbase
User ID: test-user
Scope: read
Status: active
Language: en
Created: 2025-01-06 12:00:00
Updated: 2025-01-06 12:00:00
```

#### Step 3: Reuse Token in Next Test (Skip Re-Auth)

When creating a link token, use the stored token to skip the authentication UI:

```bash
meshc link-token \
  --user-id test-user \
  --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX \
  --symbol USDC \
  --use-stored-tokens
```

Logs:
```
INFO: found 1 stored token(s) for user test-user
Link Token: aHR0cHM6Ly9zYW5kYm94LXdlYi...
```

When you open this link token in the browser, **Coinbase authentication is skipped**—the UI goes straight to "Select amount" or "Confirm transfer".

### Multi-Integration Testing

Store tokens from different exchanges and test them in sequence:

```bash
# Store Coinbase token
meshc token-store \
  --token-id "tok_coinbase_xyz" \
  --integration-type Coinbase \
  --user-id alice \
  --scope read

# Store Binance token
meshc token-store \
  --token-id "tok_binance_xyz" \
  --integration-type Binance \
  --user-id alice \
  --scope read

# Store MetaMask wallet token
meshc token-store \
  --token-id "tok_metamask_xyz" \
  --integration-type MetaMask \
  --wallet-address "0x742d35Cc6634C0532925a3b844Bc9e7595f92BD8" \
  --scope write

# List all tokens for user
meshc token-list --user-id alice
```

Output:
```
Token ID                       Type            User/Wallet               Scope  Lang Status
===============================================================================================
tok_binance_xyz...             Binance         alice                     read   en   active
tok_coinbase_xyz...            Coinbase        alice                     read   en   active

Total: 2 token(s)
```

Then test with all stored tokens:

```bash
meshc link-token \
  --user-id alice \
  --address GADDR... \
  --symbol USDC \
  --use-stored-tokens
```

All three integrations (Coinbase, Binance, MetaMask) are now available in the UI without re-authentication.

### Language Preferences

Store user language preferences alongside tokens:

```bash
# French user
meshc token-store \
  --token-id "tok_user_fr" \
  --integration-type Coinbase \
  --user-id user_paris \
  --lang fr

# Spanish user
meshc token-store \
  --token-id "tok_user_es" \
  --integration-type Binance \
  --user-id user_madrid \
  --lang es

# List by language (check the 'Lang' column)
meshc token-list
```

The `lang` field is useful for tracking user preferences in logs and analytics.

### Token Management

#### Revoke a Token (Soft Delete)

Soft-revoke keeps the token for audit trail but marks it inactive:

```bash
meshc token-revoke tok_test_coinbase_abc123
```

Output:
```
revoked token: tok_test_coinbase...
```

Verify it's revoked:

```bash
meshc token-list
# Status shows 'revoked' instead of 'active'

meshc token-list --active-only
# Token no longer appears (only active tokens shown)
```

#### Test Multiple User Scenarios

```bash
# User 1: Has Coinbase token
meshc token-store \
  --token-id "tok_alice_cb" \
  --integration-type Coinbase \
  --user-id alice

# User 2: Has MetaMask token
meshc token-store \
  --token-id "tok_bob_mm" \
  --integration-type MetaMask \
  --user-id bob \
  --wallet-address "0x742d35Cc6634C0532925a3b844Bc9e7595f92BD8"

# User 3: Has no tokens (tests fresh auth flow)

# Test each user scenario
meshc link-token --user-id alice --address GADDR... --symbol USDC --use-stored-tokens
# Alice sees Coinbase pre-authenticated

meshc link-token --user-id bob --address 0x... --symbol USDC --network-id ethereum-sepolia --use-stored-tokens
# Bob sees MetaMask pre-authenticated

meshc link-token --user-id charlie --address GADDR... --symbol USDC
# Charlie sees all exchanges (no stored tokens)
```

### Database Location

Token database is stored at: `~/.meshc/tokens.db`

View the path and structure:

```bash
ls -la ~/.meshc/tokens.db

# Delete to reset (creates fresh database on next token-store)
rm ~/.meshc/tokens.db
```

Custom path via environment variable:

```bash
export MESHC_TOKEN_DB="/tmp/test_tokens.db"
meshc token-list  # Uses /tmp/test_tokens.db
```

### Common Test Workflows

**Workflow 1: Test Token Reuse**
```bash
# 1. Store a token
meshc token-store --token-id tok123 --integration-type Coinbase --user-id test

# 2. Create link token with stored tokens
meshc link-token --user-id test --address GADDR... --symbol USDC --use-stored-tokens

# 3. Verify in browser: Coinbase auth UI is skipped
```

**Workflow 2: Test Multi-Exchange Setup**
```bash
# Store tokens for 2 exchanges
meshc token-store --token-id tok_cb --integration-type Coinbase --user-id alice
meshc token-store --token-id tok_bn --integration-type Binance --user-id alice

# Test with all tokens
meshc link-token --user-id alice --address GADDR... --symbol USDC --use-stored-tokens
# Sees Coinbase + Binance pre-authenticated in UI
```

**Workflow 3: Test User Offboarding (Revoke Tokens)**
```bash
# User revokes all their tokens
meshc token-list --user-id alice
meshc token-revoke tok_cb
meshc token-revoke tok_bn

# Verify revocation
meshc token-list --user-id alice --active-only
# No tokens shown (all revoked)
```

---

## What's Next?

After sandbox testing works:

1. **Production keys** → Generate in Mesh Dashboard
2. **Webhooks** → Configure endpoint to receive transfer events
3. **Frontend integration** → Use `@meshconnect/web-link-sdk` npm package

```javascript
// Example frontend code
import { createLink } from "@meshconnect/web-link-sdk";

const meshLink = createLink({
  clientId: "YOUR_CLIENT_ID",
  onTransferFinished: (result) => {
    console.log("Transfer:", result.status);
  },
});

// linkToken comes from your backend (meshc link-token)
meshLink.openLink(linkToken);
```

---

## Files in This Project

```
meshc/
├── local_settings.py      # Your API credentials (gitignored)
├── src/meshc/
│   ├── core.py            # API functions (create_link_token, etc.)
│   ├── cli.py             # CLI commands
│   ├── config.py          # Configuration loading
│   └── errors.py          # Error code dictionary
└── TESTING.md             # This file
```
