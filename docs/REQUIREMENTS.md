# meshc: Mesh Deposit Flow Mockup

## Overview

A Python CLI and library for simulating Coinbase deposit flows via the Mesh Connect API. Designed for testing and development of Mesh integrations without a full frontend stack.

---

## Goals

1. **Dual-use**: Importable library + standalone CLI
2. **Unix philosophy**: stdin/stdout, proper exit codes, composable
3. **Clean separation**: Library logic has no I/O; CLI is a thin adapter
4. **Mockup focus**: Simulate the Mesh deposit flow for Coinbase integration testing

---

## Project Structure

```
meshc/
├── pyproject.toml
├── src/meshc/
│   ├── __init__.py       # Package exports
│   ├── __main__.py       # python -m meshc entry point
│   ├── core.py           # Library logic (API calls, data models)
│   ├── cli.py            # CLI wrapper (argparse, I/O)
│   └── config.py         # Configuration handling
└── tests/
    ├── __init__.py
    ├── test_core.py
    └── test_cli.py
```

---

## Core Library (`core.py`)

### Responsibilities

- Create Mesh link tokens via API
- Query transfer status
- Fetch supported networks
- Parse and validate responses

### API Functions

```python
def create_link_token(
    client_id: str,
    client_secret: str,
    user_id: str,
    to_addresses: list[dict],
    *,
    transfer_type: str = "deposit",
    transaction_id: str | None = None,
    enable_smart_funding: bool = True,
    integration_id: str | None = None,  # e.g., Coinbase integration ID
    api_url: str = "https://sandbox-integration-api.meshconnect.com",
) -> dict:
    """
    Create a Mesh link token for deposit flow.

    Returns: {"link_token": str, "expires_at": str, ...}
    Raises: MeshAPIError on failure
    """

def get_transfer_status(
    client_id: str,
    client_secret: str,
    transaction_id: str,
    *,
    api_url: str = "https://sandbox-integration-api.meshconnect.com",
) -> dict:
    """
    Poll transfer status from Mesh API.

    Returns: {"status": str, "amount": float, "symbol": str, "tx_hash": str | None}
    Raises: MeshAPIError on failure
    """

def get_networks(
    client_id: str,
    client_secret: str,
    *,
    api_url: str = "https://sandbox-integration-api.meshconnect.com",
) -> list[dict]:
    """
    Fetch supported networks and tokens.

    Returns: [{"id": str, "name": str, "tokens": list, ...}, ...]
    """

def get_stellar_network_id(
    client_id: str,
    client_secret: str,
    *,
    api_url: str = "https://sandbox-integration-api.meshconnect.com",
) -> str:
    """
    Convenience: Get the Stellar network ID.

    Returns: UUID string for Stellar network
    Raises: MeshAPIError if Stellar not found
    """
```

### Data Classes

```python
@dataclass
class ToAddress:
    symbol: str       # e.g., "USDC", "XLM", "EURC"
    address: str      # Destination wallet address
    network_id: str   # Mesh network UUID
    amount: float | None = None  # Optional for SmartFunding

@dataclass
class TransferStatus:
    status: str           # "pending", "succeeded", "failed"
    amount: float | None
    symbol: str | None
    tx_hash: str | None   # On-chain transaction hash
    raw: dict             # Full API response

@dataclass
class LinkToken:
    token: str
    expires_at: str | None
    pay_link: str | None  # If generatePayLink=true
    raw: dict
```

### Exception Classes

```python
class MeshError(Exception):
    """Base exception for Mesh operations."""

class MeshAPIError(MeshError):
    """API request failed."""
    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        ...

class MeshConfigError(MeshError):
    """Configuration missing or invalid."""
```

### Library Rules

- No `print()` calls
- Return structured data or raise exceptions
- All API calls use `httpx` (async-friendly, modern)
- Type hints on all public functions
- Logging via `logging` module (caller controls handlers)

---

## Configuration (`config.py`)

### Sources (priority order)

1. Function arguments (highest)
2. Environment variables
3. `local_settings.py` in current directory

### Environment Variables

```bash
MESH_CLIENT_ID       # Required
MESH_CLIENT_SECRET   # or MESH_SECRET
MESH_API_URL         # or MESH_API (default: sandbox URL)
MESH_STELLAR_NETWORK_ID  # Optional, fetched if not set
```

### local_settings.py Format

```python
# local_settings.py (in project root, gitignored)
MESH_CLIENT_ID = "358ef0a7-..."
MESH_SECRET = "sk_sand_..."
MESH_API = "https://sandbox-integration-api.meshconnect.com"

# Optional
MESH_STELLAR_NETWORK_ID = "06855704-43d2-4ad2-a73c-372f0c3534e1"
MESH_TRANSFER_TYPE = "deposit"
MESH_ENABLE_SMART_FUNDING = True
```

### Config Function

```python
def load_config(
    client_id: str | None = None,
    client_secret: str | None = None,
    **overrides,
) -> dict:
    """
    Load configuration from env, local_settings.py, and overrides.
    Returns merged config dict.
    Raises: MeshConfigError if required values missing.
    """
```

---

## CLI (`cli.py`)

### Commands

```bash
# Create link token for deposit
meshc link-token \
    --user-id USER123 \
    --address GADDR... \
    --symbol USDC \
    [--amount 100.00] \
    [--network-id UUID] \
    [--integration-id COINBASE_ID] \
    [--json]

# Check transfer status
meshc status TX_ID [--json] [--poll] [--interval 5]

# List networks
meshc networks [--json] [--filter stellar]

# Get Stellar network ID
meshc stellar-network-id

# Simulate full deposit flow (mock mode)
meshc mock-deposit \
    --user-id USER123 \
    --address GADDR... \
    --symbol USDC \
    --amount 100.00

# Read config from stdin (for piping)
echo '{"user_id": "x", "address": "y"}' | meshc link-token --stdin
```

### Output Modes

- **Default**: Human-readable to stdout
- **`--json`**: JSON output for scripting
- **Errors**: Always to stderr
- **Exit codes**: 0=success, 1=error, 2=usage error

### CLI Structure

```python
def main(argv: list[str] | None = None) -> int:
    """
    Main entry point.
    Returns exit code (0=success, non-zero=error).
    """

def cmd_link_token(args: argparse.Namespace) -> int:
    """Handle 'link-token' subcommand."""

def cmd_status(args: argparse.Namespace) -> int:
    """Handle 'status' subcommand."""

def cmd_networks(args: argparse.Namespace) -> int:
    """Handle 'networks' subcommand."""

def cmd_mock_deposit(args: argparse.Namespace) -> int:
    """Handle 'mock-deposit' subcommand (simulation mode)."""
```

### CLI Rules

- Parse args with `argparse`
- Read stdin if `--stdin` flag or no required args
- Write results to stdout
- Write errors to stderr
- Return proper exit codes
- No business logic—delegate to `core.py`

---

## Mock Deposit Flow (`mock-deposit` command)

### Purpose

Simulate the full Mesh deposit flow without a browser/frontend:

1. Create link token
2. (Mock) User selects Coinbase integration
3. (Mock) User authenticates and approves transfer
4. Poll for transfer status
5. Report final status

### Mock Behavior

```python
def simulate_deposit(
    user_id: str,
    address: str,
    symbol: str,
    amount: float,
    *,
    delay_seconds: float = 2.0,  # Simulate processing time
    success_rate: float = 0.95,  # 95% success for testing
) -> TransferStatus:
    """
    Simulate a deposit flow for testing.

    1. Creates real link token via Mesh API
    2. Simulates user interaction (no actual transfer)
    3. Returns mock TransferStatus

    Useful for integration testing without real funds.
    """
```

### Mock vs Real Mode

- **Mock mode** (`mock-deposit`): Simulates transfer, no real API calls after link token
- **Real mode** (`link-token` + `status`): Actual API interactions

---

## Dependencies

### Required

```toml
[project]
dependencies = [
    "httpx>=0.27",      # HTTP client
    "tomli>=2.0",       # TOML parsing (Python <3.11)
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-httpx",     # HTTP mocking
    "ruff",             # Linting
    "mypy",             # Type checking
]
```

### Why These

- **httpx**: Modern async-capable HTTP client, cleaner than requests
- **tomli**: TOML config files (stdlib in 3.11+, backport for 3.10)
- **No Click/Typer**: Simple subcommand structure works fine with argparse

---

## Entry Points

```toml
[project.scripts]
meshc = "meshc.cli:main"
```

```python
# src/meshc/__main__.py
from meshc.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
```

---

## Usage Examples

### As Library

```python
from meshc import create_link_token, get_transfer_status, ToAddress

# Create link token
addresses = [
    ToAddress(symbol="USDC", address="GADDR...", network_id="0685..."),
]
result = create_link_token(
    client_id="...",
    client_secret="...",
    user_id="user123",
    to_addresses=[a.__dict__ for a in addresses],
)
print(result["link_token"])

# Check status
status = get_transfer_status(
    client_id="...",
    client_secret="...",
    transaction_id="tx123",
)
if status["status"] == "succeeded":
    print(f"Deposited {status['amount']} {status['symbol']}")
```

### As CLI

```bash
# Set credentials
export MESH_CLIENT_ID="..."
export MESH_CLIENT_SECRET="..."

# Create link token
meshc link-token --user-id user123 --address GADDR... --symbol USDC

# Poll status until complete
meshc status tx123 --poll --interval 3

# Pipe JSON config
echo '{"user_id":"x","address":"y","symbol":"USDC"}' | meshc link-token --stdin --json

# Mock full flow
meshc mock-deposit --user-id user123 --address GADDR... --symbol USDC --amount 50
```

---

## Testing Strategy

### Unit Tests

- `test_core.py`: Mock HTTP responses, test parsing and error handling
- `test_config.py`: Test config loading priority
- `test_cli.py`: Test argument parsing and output formatting

### Integration Tests (optional, requires creds)

```bash
MESH_TEST_INTEGRATION=1 pytest tests/ -m integration
```

### Test Fixtures

```python
# conftest.py
@pytest.fixture
def mock_mesh_api(httpx_mock):
    """Configure mock responses for Mesh API."""
    httpx_mock.add_response(
        url__startswith="https://sandbox-integration-api.meshconnect.com",
        json={"content": {"linkToken": "mock_token_123"}},
    )
    return httpx_mock
```

---

## Error Handling

### Library Errors

```python
# All errors derive from MeshError
try:
    result = create_link_token(...)
except MeshAPIError as e:
    logger.error(f"API call failed: {e} (status={e.status_code})")
except MeshConfigError as e:
    logger.error(f"Configuration error: {e}")
```

### CLI Errors

```bash
$ meshc link-token --user-id x
Error: MESH_CLIENT_ID not set
$ echo $?
1

$ meshc link-token --invalid-flag
usage: meshc link-token [-h] ...
meshc: error: unrecognized arguments: --invalid-flag
$ echo $?
2
```

---

## Logging

### Library

```python
import logging
logger = logging.getLogger("meshc")

# Library logs at DEBUG/INFO level
# Caller decides how to handle
logger.debug("Creating link token for user %s", user_id)
logger.info("Transfer %s completed: %s %s", tx_id, amount, symbol)
```

### CLI

```bash
# Verbose mode enables INFO logging
meshc --verbose link-token ...

# Debug mode enables DEBUG logging
meshc --debug link-token ...
```

---

## Security Notes

1. **Never log secrets**: `client_secret` is masked in logs
2. **Env over args**: Prefer env vars for secrets (not visible in `ps`)
3. **Config file permissions**: Warn if config file is world-readable
4. **Sandbox default**: Default to sandbox API URL to prevent accidents

---

## Future Considerations (Out of Scope)

- Webhook server for receiving callbacks
- Full SEP-24 integration with Polaris
- Browser automation for real Coinbase OAuth
- Multi-asset portfolio simulation

---

## Version

- Python: 3.10+
- Initial release: 0.1.0
