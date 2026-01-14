# IntegrationToken Testing Plan

## 1. Test CLI Token Commands

From project root:

```bash
# Activate venv
source .venv/bin/activate

# Store a test token

meshc token-store --token-id test-token-123 --integration-type Coinbase --user-id testuser1 --lang en
# List tokens (should show the new token)
meshc token-list

# Get specific token
meshc token-get test-token-123

# Revoke the token
meshc token-revoke test-token-123

# List again (status should be 'revoked')
meshc token-list

# Store another for Django admin test
meshc token-store admin-test-456 Binance --user-id webuser --wallet-address 0x1234567890abcdef
```

## 2. Test Django Admin

```bash
# Start Django server
cd meshc_django
source ../.venv/bin/activate
python manage.py runserver

# Open browser: http://localhost:8000/admin/
# Login with superuser credentials

# Navigate to: Meshsbox > Integration Tokens
# You should see tokens created via CLI
```

### Create superuser (if not exists):
```bash
cd meshc_django
python manage.py createsuperuser
# Enter username, email, password
```

### Verify in Admin:
1. **List View**: Check tokens appear with correct columns
2. **Filters**: Test status/integration_type filters work
3. **Search**: Search by token_id or user_id
4. **Bulk Action**: Select tokens, use "Revoke selected tokens" action
5. **Detail View**: Click a token, verify all fields display

## 3. Verify Shared Database

```bash
# After creating token in admin, check via CLI:
meshc token-list

# After creating token via CLI, refresh admin page
# Both should show same tokens
```

## 4. Quick Smoke Test

```bash
# One-liner to test full cycle:
cd /home/antb2/dev/rsync/meshc
source .venv/bin/activate

# Create, list, verify
meshc token-store smoke-test-$(date +%s) MetaMask --user-id smoke && \
meshc token-list | head -5
```

## Expected Database Location

Both CLI and Django use: `meshc_django/db.sqlite3`

To verify:
```bash
sqlite3 meshc_django/db.sqlite3 "SELECT token_id, integration_type, status FROM integration_tokens LIMIT 5;"
```
