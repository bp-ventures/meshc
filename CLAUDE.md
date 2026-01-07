# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`meshc` is a CLI and library for Mesh Connect deposit flows. It wraps the Mesh API to create link tokens that enable users to transfer crypto from exchanges (Coinbase, Binance) or wallets (MetaMask) to your application.

## Commands

```bash
# Setup
uv venv && source .venv/bin/activate
uv pip install -e .
uv pip install -e ".[dev]"  # with dev dependencies

# Run CLI
meshc networks                    # List supported networks
meshc sandbox-cex --open          # Test exchange flow (opens browser)
meshc sandbox-wallet --address 0x... --open  # Test wallet flow (Sepolia testnet)

# Tests
pytest                           # Run all tests
pytest tests/test_core.py        # Run specific test file
pytest -k "test_create_link"     # Run tests matching pattern
pytest -v                        # Verbose output

# Linting
ruff check src/                  # Check for issues
ruff check --fix src/            # Auto-fix issues
mypy src/                        # Type checking
```

## Architecture

```
src/meshc/
├── __init__.py   # Public API exports
├── core.py       # API functions (create_link_token, get_networks, simulate_deposit)
├── cli.py        # argparse CLI - thin adapter that calls core functions
├── config.py     # Configuration loading (env vars → local_settings.py → defaults)
├── storage.py    # Token storage backend (Peewee ORM, SQLite)
└── errors.py     # Mesh error codes and human-readable descriptions
```

**Key design pattern**: `cli.py` is a thin wrapper that parses args and calls pure functions in `core.py`. All API logic lives in `core.py`.

## Configuration

Credentials load from (highest to lowest priority):
1. Function arguments
2. Environment variables (`MESH_CLIENT_ID`, `MESH_SECRET`, `MESH_API`)
3. `local_settings.py` in current directory (Django-style uppercase vars)

Token storage defaults to `~/.meshc/tokens.db` (SQLite).

## Testing Against Mesh API

Two sandbox modes:
- **CEX (exchange)**: Mocked data, any credentials work (`user123`/`pass123`)
- **Wallet**: Real Sepolia testnet transactions (need Sepolia ETH from faucet)

Use `meshc sandbox-cex --open` or `meshc sandbox-wallet --address 0x... --open` to generate link tokens and auto-open in browser.

## Dependencies

- `httpx` - HTTP client for API calls
- `peewee` - ORM for token storage (SQLite)
- `pytest-httpx` - Mock HTTP in tests
