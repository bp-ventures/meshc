# Mesh Connect Test Cases

Comprehensive test cases for meshc CLI and Mesh Connect integration.

**Focus**: Stellar network, Coinbase exchange, own wallet integration.

TESTNET SEPOLA ACCCOUNT:
Recovery phrase: guard blade room burden exit sphere dish open tiger pause organ fluid
public key: 0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c


STELLAR (default test account):
Public:  GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX
Secret:  SD2VS55L2C2HGIQFN3NUQ46GJX4W47BNAN6PNILW3JKQEHDAXVJD2HPS



---

## Sandbox Tests (Mocked Data)

### CEX Exchange Flows (Coinbase)

All CEX sandbox tests use mocked data. Use Any credentials displayed (e.g., `MeshUser`/`Pass123`).

| # | Test Case | Command | Expected Result |
|---|-----------|---------|-----------------|
| S1 | Withdraw USDC from Coinbase (default) | `meshc sandbox-cex --open` | Link opens, mock transfer succeeds |
| S2 | Withdraw ETH from Coinbase | `meshc sandbox-cex --symbol ETH --open` | Mock ETH transfer |
| S3 | Withdraw XLM from Coinbase | `meshc sandbox-cex --symbol XLM --open` | Mock XLM transfer |
| S4 | Withdraw with custom amount | `meshc sandbox-cex --amount 100 --open` | 100 USDC transfer |
| S5 | Withdraw with custom user ID | `meshc sandbox-cex --user-id my-user-123 --open` | UserId in payload matches |
| S6 | Withdraw with client fee | `meshc sandbox-cex --client-fee 0.025 --open` | 2.5% fee applied |
| S7 | Withdraw with SmartFunding disabled | `meshc sandbox-cex --no-smart-funding --open` | SmartFunding off |
| S8 | Custom transaction ID | `meshc sandbox-cex --transaction-id test-tx-001 --open` | TransactionId matches |
| S9 | Spanish language UI | `meshc sandbox-cex --lang es --open` | UI in Spanish |

### Wallet Flows (Sepolia Testnet)

Wallet sandbox tests use real Sepolia testnet. Requires Sepolia ETH from faucet. Provided wallet has funds

| # | Test Case | Command | Expected Result |
|---|-----------|---------|-----------------|
| S10 | Wallet connect (MetaMask) | `meshc sandbox-wallet --address 0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c --open` | Connect MetaMask on Sepolia |
| S11 | Wallet with small amount | `meshc sandbox-wallet --address 0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c --amount 0.0001 --open` | 0.0001 ETH transfer |
| S12 | CEX with USDC on Stellar | `meshc sandbox-cex --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX --symbol USDC --open` | USDC on Stellar |

---

## VPN/Geo Tests (Exchange Availability)

Exchange availability varies by country. Test with VPN to verify Mesh shows correct exchanges.

| # | Test Case | VPN Location | Expected Exchanges | Notes |
|---|-----------|--------------|-------------------|-------|
| V1 | US user | United States | Coinbase, | Binance NOT available |
| V2 | UK user | United Kingdom | Coinbase, Binance | Full availability |
| V3 | France user | France | Coinbase, Binance | EU regulations |
| V4 | Canada user | Canada | Coinbase | Binance restricted |
| V5 | Nigeria user | Nigeria | Binance, others | Coinbase may be limited |

### VPN Test Procedure

1. Connect to VPN for target country
2. Run `meshc sandbox-cex --open`
3. Observe which exchanges appear in the Mesh Link UI
4. Document available exchanges
5. Repeat for each country

**Note**: Binance availability is heavily geo-restricted. US users will NOT see Binance.

---

## Testnet Tests (Sepolia/Stellar Testnet)

Real transactions on test networks. No real funds at risk.

### Stellar Testnet

| # | Test Case | Command | Expected Result |
|---|-----------|---------|-----------------|
| T1 | Deposit USDC to Stellar testnet | `meshc sandbox-cex --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX --network-id {stellar-testnet-id} --open` | USDC arrives on Stellar testnet |
| T2 | Deposit XLM to Stellar testnet | `meshc sandbox-cex --symbol XLM --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX --open` | XLM arrives |

### Ethereum Sepolia

| # | Test Case | Command | Expected Result |
|---|-----------|---------|-----------------|
| T3 | Deposit ETH to Sepolia | `meshc sandbox-wallet --address 0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c --symbol ETH --amount 0.0001 --open` | 0.0001 ETH arrives on Sepolia |
| T4 | Deposit USDC to Stellar | `meshc sandbox-cex --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX --symbol USDC --open` | USDC arrives on Stellar |

---

## Production Tests (Real Funds) - Coinbase Focus

**WARNING**: These tests use real funds. Use minimum amounts.

### Coinbase Stellar Withdrawals

| # | Test Case | Command | Expected Result |
|---|-----------|---------|-----------------|
| P1 | Withdraw 1 USDC to Stellar | `meshc deposit --symbol USDC --amount 1 --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX --open` | 1 USDC arrives on Stellar |
| P2 | Withdraw 1 XLM to Stellar | `meshc deposit --symbol XLM --amount 1 --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX --open` | 1 XLM arrives on Stellar |

### Coinbase Auto-Convert

| # | Test Case | Command | Expected Result |
|---|-----------|---------|-----------------|
| P5 | Withdraw 1 EURC (auto-convert) | `meshc deposit --symbol EURC --amount 1 --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX --open` | EURC arrives (converted) |
| P6 | Withdraw 1 USDC with EUR source | `meshc deposit --symbol USDC --amount 1 --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX --open` | USDC arrives (converted from EUR if needed) |


### Coinbase Edge Cases

| # | Test Case | Command | Expected Result |
|---|-----------|---------|-----------------|
| P9 | Withdraw with 2.5% client fee | `meshc deposit --symbol USDC --amount 10 --client-fee 0.025 --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX --open` | Fee deducted, ~9.75 USDC arrives |

### Wallet Transfers (MetaMask Mainnet)

| # | Test Case | Command | Expected Result |
|---|-----------|---------|-----------------|
| P11 | Transfer 0.0001 ETH from MetaMask | `meshc deposit --symbol ETH --amount 0.0001 --address 0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c --open` → MetaMask | 0.0001 ETH transferred |

---

## Webhook Validation Tests

### Mock Webhook Tests

| # | Test Case | Command | Expected Result |
|---|-----------|---------|-----------------|
| W1 | Send Succeeded webhook | `python scripts/mock_webhook.py --status Succeeded` | HTTP 200, payload received |
| W2 | Send Pending webhook | `python scripts/mock_webhook.py --status Pending` | HTTP 200, status=Pending |
| W3 | Send Failed webhook | `python scripts/mock_webhook.py --status Failed` | HTTP 200, status=Failed |
| W4 | Webhook with Coinbase provider | `python scripts/mock_webhook.py --provider Coinbase` | SourceAccountProvider=Coinbase |
| W5 | Webhook with ETH on Ethereum | `python scripts/mock_webhook.py --symbol ETH --network-id 03b2d786-7092-4a6a-9737-d6013e21819b` | Chain=Ethereum, Token=ETH |
| W6 | Webhook with custom amount | `python scripts/mock_webhook.py --amount 123.45` | SourceAmount=123.45 |
| W7 | Webhook with custom user ID | `python scripts/mock_webhook.py --user-id prod-user-456` | UserId matches |
| W8 | Dry run (no send) | `python scripts/mock_webhook.py --dry-run` | Payload printed, not sent |

### Webhook Payload Validation

| # | Test Case | Validation | Expected |
|---|-----------|------------|----------|
| W9 | Verify Id field | UUID format | Valid UUID v4 |
| W10 | Verify EventId field | UUID format | Valid UUID v4 |
| W11 | Verify SentTimestamp | Unix seconds | Recent timestamp |
| W12 | Verify Timestamp | Unix milliseconds | SentTimestamp * 1000 |
| W13 | Verify TxHash format (Stellar) | 64 hex chars | No 0x prefix |
| W14 | Verify TxHash format (Ethereum) | 0x + 64 hex | Has 0x prefix |

### Webhook Integration Tests

| # | Test Case | Steps | Expected |
|---|-----------|-------|----------|
| W15 | End-to-end webhook flow | 1. Create link token<br>2. Complete transfer<br>3. Check webhook.site | Webhook received with correct TransactionId |
| W16 | Verify webhook against API | 1. Receive webhook<br>2. Call `meshc status {tx_id}` | API status matches webhook |

---



### Error Handling

| # | Test Case | Condition | Expected |
|---|-----------|-----------|----------|
| A5 | Missing credentials | No MESH_CLIENT_ID | Clear error message |
| A6 | Invalid credentials | Wrong client secret | API error with code |
| A7 | Invalid network ID | Non-existent network | API error |
| A8 | Invalid symbol | Unsupported token | API error |

---

## Configuration Tests

| # | Test Case | Method | Expected |
|---|-----------|--------|----------|
| C1 | Load from local_settings.py | Set vars in file | Config loaded |
| C2 | Load from environment | `MESH_CLIENT_ID=... meshc ...` | Env vars used |
| C3 | CLI override | `meshc --client-id ... --client-secret ...` | CLI args take priority |
| C4 | Webhook URL from settings | `MESH_WEBHOOK_URL` in local_settings.py | Webhook URL loaded |

---

## Test Execution Checklist

### Before Testing

- [ ] Copy `local_settings.py.example` to `local_settings.py`
- [ ] Fill in `MESH_CLIENT_ID` and `MESH_SECRET`
- [ ] Set `MESH_WEBHOOK_URL` to your webhook.site URL
- [ ] Activate virtual environment: `source .venv/bin/activate`

### Sandbox Testing (No Real Funds)

- [ ] Run S1-S9 (CEX sandbox tests with Coinbase)
- [ ] Run S10-S12 (Wallet sandbox tests)
- [ ] Run W1-W8 (mock webhook tests)
- [ ] Run A1-A4 (API tests)

### VPN/Geo Testing

- [ ] Run V1-V5 (test exchange availability by country)
- [ ] Document which exchanges appear in each region

### Testnet Testing (Test Networks)

- [ ] Get Sepolia ETH from faucet
- [ ] Run T1-T4 (testnet tests)
- [ ] Verify transactions on block explorers

### Production Testing (Real Funds - Coinbase)

- [ ] Use minimum amounts (1 USDC, 1 XLM, 0.0001 ETH)
- [ ] Run P1-P4 (basic Stellar withdrawals)
- [ ] Run P5-P6 (auto-convert tests)
- [ ] Run P7-P8 (small ETH withdrawals)
- [ ] Run P9-P10 (edge cases)
- [ ] Verify funds arrive at destination
- [ ] Verify webhook received

---

## Network IDs Reference

| Network | Network ID | Chain |
|---------|------------|-------|
| Stellar (mainnet) | `06855704-43d2-4ad2-a73c-372f0c3534e1` | Stellar |
| Ethereum Sepolia | `03b2d786-7092-4a6a-9737-d6013e21819b` | Ethereum |

Use `meshc networks` to get the full list of supported networks.

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "MESH_CLIENT_ID not set" | Missing credentials | Add to local_settings.py |
| "CEX sandbox testing requires sandbox API URL" | Using production URL | Use sandbox URL for CEX tests |
| Transfer not found in status | Sandbox limitation | Sandbox transfers may not persist to API |
| Webhook not received | Wrong URL | Verify MESH_WEBHOOK_URL in settings |
| Binance not showing | Geo-restriction | US users cannot access Binance via Mesh |
| Exchange list varies | Country detection | Use VPN to test different regions |
