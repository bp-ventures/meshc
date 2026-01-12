# CLI Simplification Refactor (January 12, 2026)

## Overview

Simplify the meshc CLI by removing 2 redundant commands:
- `sandbox-wallet` → merge into `sandbox-cex --wallet`
- `stellar-id` → use `networks --filter stellar`

**Before:** 12 commands | **After:** 10 commands

---

## Changes Summary

### 1. Merge `sandbox-wallet` into `sandbox-cex`

**Old (two commands):**
```bash
meshc sandbox-cex --open                              # CEX/exchange testing
meshc sandbox-wallet --address 0x... --open           # Wallet testing
```

**New (single command with flag):**
```bash
# CEX mode (default) - uses Stellar testnet
meshc sandbox-cex --open

# Wallet mode - uses Sepolia testnet
meshc sandbox-cex --wallet --address 0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c --open
```

### 2. Remove `stellar-id` Command

**Old:**
```bash
meshc stellar-id
```

**New (use networks filter):**
```bash
meshc networks --filter stellar --json | jq '.[0].id'
```

---

## Test Accounts Reference

| Network | Address | Usage |
|---------|---------|-------|
| Stellar testnet | `GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX` | Default for `sandbox-cex` |
| Sepolia testnet | `0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c` | Use with `--wallet` flag |

**Sepolia Faucet:** https://cloud.google.com/application/web3/faucet/ethereum/sepolia

---

## Migration Guide

| Old Command | New Command |
|-------------|-------------|
| `meshc sandbox-wallet --address 0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c --open` | `meshc sandbox-cex --wallet --address 0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c --open` |
| `meshc stellar-id` | `meshc networks --filter stellar --json` |

---

## Quick Test Commands

```bash
# Test CEX mode (Stellar) - no changes needed
meshc sandbox-cex --open
meshc sandbox-cex --address GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX --open

# Test wallet mode (Sepolia) - use --wallet flag
meshc sandbox-cex --wallet --address 0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c --open

# Get Stellar network ID (replacement for stellar-id)
meshc networks --filter stellar --json

# Verify command count
meshc --help  # Should show 10 commands
```

---

## Files Modified

| File | Changes |
|------|---------|
| `src/meshc/cli.py` | Removed `sandbox-wallet` and `stellar-id` commands, added `--wallet` flag to `sandbox-cex` |
| `src/meshc/__init__.py` | Removed `create_sandbox_wallet_token` and `get_stellar_network_id` from exports |
| `docs/CLI.md` | Updated command reference |

---

## Rationale

1. **`sandbox-wallet`** was nearly identical to `sandbox-cex` - just different network defaults. The `--wallet` flag makes the relationship explicit.

2. **`stellar-id`** was a single hardcoded value that could be retrieved via `networks --filter`. Removing it reduces API surface without losing functionality.

3. **`mock-deposit`** was kept - it provides value for local testing without requiring browser interaction.
