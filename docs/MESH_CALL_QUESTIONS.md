# Mesh Call Questions

Cleaned up based on sandbox testing and documentation review.

---

## Network & Integration IDs

1. **Are network IDs static?**
   - We're caching `06855704-43d2-4ad2-a73c-372f0c3534e1` (Stellar) and `03b2d786-7092-4a6a-9737-d6013e21819b` (Sepolia)
   - Safe to hardcode, or should we fetch on startup?

2. **What's the Coinbase `integrationId`?**
   - To skip the catalog and go directly to Coinbase
   - Does this ID ever change?

---

## Sandbox vs Production

~~3. Do sandbox transfers move test funds?~~
**ANSWERED**: CEX = fully mocked, Wallet = real Sepolia testnet transactions

~~4. Test Coinbase credentials?~~
**ANSWERED**: Use ANY credentials (e.g., `user123`/`pass123`) for sandbox CEX

5. **Any differences in rate limits between sandbox and production?**

---

## Transfer Flow

6. **Can a transfer be cancelled after initiation?**
   - If yes, at what stage? Before user confirms? After?

7. **What happens if user closes browser mid-transfer?**
   - Does it continue? Fail? Enter pending state?

8. **How long is a `linkToken` valid?**
   - We see `expiresAt` in response—what's the typical TTL?

---

## SmartFunding

9. **How are conversion rates determined?**
   - Exchange's native rate? Mesh's aggregated rate?
   - Any slippage protection?

10. **Min/max limits for SmartFunding?**
    - Per-exchange limits, or Mesh-wide?

---

## Error Handling

~~11. What are common failure modes?~~
**ANSWERED**: Documented in error dictionary (InsufficientFunds, KycRequired, etc.)

12. **Is there automatic retry on failure?**
    - Or must user restart the flow?

---

## Coinbase-Specific

13. **Does Mesh handle OAuth token refresh?**
    - Or do we need to manage token lifecycle?

14. **Coinbase Advanced Trade supported?**
    - Or only regular Coinbase consumer accounts?

---

## Security

15. **How long are access tokens stored?**
    - Can we request deletion for a user?

---

## Summary: 10 Questions for the Call

| # | Question | Priority |
|---|----------|----------|
| 1 | Are network IDs static? Safe to cache? | High |
| 2 | What's the Coinbase integrationId? | High |
| 3 | Rate limit differences sandbox vs prod? | Medium |
| 4 | Can transfers be cancelled mid-flow? | Medium |
| 5 | Browser closed mid-transfer behavior? | Medium |
| 6 | linkToken TTL? | Low |
| 7 | SmartFunding rate source + slippage? | High |
| 8 | SmartFunding min/max limits? | Medium |
| 9 | Automatic retry on failure? | Medium |
| 10 | OAuth token refresh—Mesh handles it? | High |

---

## Already Answered (Don't Ask)

| Question | Answer |
|----------|--------|
| Sandbox CEX behavior | Fully mocked, any credentials work |
| Sandbox wallet behavior | Real Sepolia testnet |
| Test Coinbase credentials | Use `user123`/`pass123` |
| Common error codes | Documented (see `meshc errors`) |
| Webhook retry policy | Verify by polling API |
| Can we add fees? | Yes, `clientFee` param (e.g., 0.025 = 2.5%) |
| Fiat amounts? | Yes, `amountInFiat` specifies USD amount |
| Provider filtering | Automatic based on token/network/geography |

---

## Good to Know (From Advanced Docs)

### Automatic Provider Filtering

Mesh automatically filters providers based on:

| Filter | What happens |
|--------|--------------|
| **Token/Network** | Only shows providers supporting the exact asset+network combo |
| **Geography** | Binance hidden in US/Canada/Netherlands; Robinhood US-only |
| **Travel Rule (VASP)** | Coinbase hidden if no VASP ID in EU countries |
| **Wallet Ownership** | Coinbase hidden for self-custody wallets >1000 EUR in EU |
| **Gaming platforms** | Binance Japan hidden for gaming use cases |

### New Parameters We Added

```bash
# Add 2.5% fee to transaction
meshc link-token ... --client-fee 0.025

# Specify $50 USD (converts to crypto at tx time)
meshc link-token ... --amount-in-fiat 50

# Include fee in displayed amount
meshc link-token ... --inclusive-fee
```
