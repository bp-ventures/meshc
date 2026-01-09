#!/usr/bin/env python3
"""Generate and send mock Mesh webhook payloads for testing.

Usage:
    python scripts/mock_webhook.py                     # Send Succeeded webhook
    python scripts/mock_webhook.py --dry-run           # Preview without sending
    python scripts/mock_webhook.py --status Failed     # Simulate failure
    python scripts/mock_webhook.py --provider Binance  # Change source exchange
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Add src to path for meshc imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx

from meshc.config import _load_local_settings, DEFAULT_STELLAR_NETWORK_ID, SEPOLIA_NETWORK_ID

# Network ID to chain name mapping
NETWORK_ID_TO_CHAIN: dict[str, str] = {
    DEFAULT_STELLAR_NETWORK_ID: "Stellar",
    SEPOLIA_NETWORK_ID: "Ethereum",
}

# Default test address (Stellar)
DEFAULT_ADDRESS = "GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX"


def generate_transaction_id() -> str:
    """Generate transaction ID: bpv + timestamp + 3 random digits."""
    ts = int(time.time())
    rand = random.randint(100, 999)
    return f"bpv{ts}{rand}"


def generate_tx_hash(chain: str) -> str:
    """Generate realistic transaction hash for the given chain."""
    if chain.lower() in ("ethereum", "sepolia"):
        # Ethereum: 0x + 64 hex chars
        return f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}"
    elif chain.lower() == "stellar":
        # Stellar: 64 hex chars (no prefix)
        return uuid.uuid4().hex + uuid.uuid4().hex[:32]
    # Default: 0x + 32 hex chars
    return f"0x{uuid.uuid4().hex}"


def network_id_to_chain(network_id: str) -> str:
    """Map network ID to chain name."""
    chain = NETWORK_ID_TO_CHAIN.get(network_id)
    if not chain:
        print(f"Warning: Unknown network ID {network_id}, using 'Unknown'", file=sys.stderr)
        return "Unknown"
    return chain


def get_webhook_url(override: str | None = None) -> str:
    """Get webhook URL from override or local_settings.py."""
    if override:
        return override
    settings = _load_local_settings()
    url = settings.get("MESH_WEBHOOK_URL")
    if not url:
        raise ValueError(
            "MESH_WEBHOOK_URL not set. Add to local_settings.py or use --webhook-url"
        )
    return url


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    """Build webhook payload from CLI arguments."""
    chain = network_id_to_chain(args.network_id)
    now = int(time.time())

    return {
        "Id": str(uuid.uuid4()),
        "EventId": str(uuid.uuid4()),
        "SentTimestamp": now,
        "UserId": args.user_id,
        "TransactionId": args.transaction_id,
        "TransferId": str(uuid.uuid4()),
        "TransferStatus": args.status,
        "TxHash": generate_tx_hash(chain),
        "Chain": chain,
        "Token": args.symbol,
        "DestinationAddress": args.address,
        "SourceAccountProvider": args.provider,
        "SourceAmount": args.amount,
        "DestinationAmount": args.amount,
        "RefundAddress": args.address,
        "Timestamp": now * 1000,
    }


def send_webhook(url: str, payload: dict[str, Any]) -> tuple[int, str]:
    """POST payload to webhook URL. Returns (status_code, response_text)."""
    headers = {
        "Content-Type": "application/json",
        "X-Mesh-Signature": "mock_signature_for_testing",
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload, headers=headers)
    return resp.status_code, resp.text


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate and send mock Mesh webhook payloads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Send Succeeded webhook with defaults
  %(prog)s --dry-run                Preview payload without sending
  %(prog)s --status Failed          Simulate a failed transfer
  %(prog)s --provider Binance       Change source exchange
  %(prog)s --amount 100 --symbol ETH  Custom transfer
""",
    )

    # Arguments matching sandbox-cex
    parser.add_argument(
        "--user-id", default="test-user",
        help="User ID (default: test-user)"
    )
    parser.add_argument(
        "--address", default=DEFAULT_ADDRESS,
        help="Destination address"
    )
    parser.add_argument(
        "--symbol", default="USDC",
        help="Token symbol (default: USDC)"
    )
    parser.add_argument(
        "--amount", type=float, default=50.0,
        help="Transfer amount (default: 50.0)"
    )
    parser.add_argument(
        "--network-id", default=DEFAULT_STELLAR_NETWORK_ID,
        help="Network ID (default: Stellar)"
    )
    parser.add_argument(
        "--transaction-id",
        help="Transaction ID (auto-generated if not provided)"
    )

    # Webhook-specific arguments
    parser.add_argument(
        "--status", default="Succeeded",
        choices=["Pending", "Succeeded", "Failed"],
        help="Transfer status (default: Succeeded)"
    )
    parser.add_argument(
        "--provider", default="Coinbase",
        help="Source account provider (default: Coinbase)"
    )
    parser.add_argument(
        "--webhook-url",
        help="Override webhook URL from local_settings.py"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print payload without sending"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Auto-generate transaction ID if not provided
    if not args.transaction_id:
        args.transaction_id = generate_transaction_id()

    # Build payload
    payload = build_payload(args)

    # Print payload
    print("Webhook Payload:")
    print("=" * 60)
    print(json.dumps(payload, indent=2))
    print()

    if args.dry_run:
        print("(dry-run mode - not sending)")
        return 0

    # Get webhook URL
    try:
        url = get_webhook_url(args.webhook_url)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Sending to: {url}")
    print()

    # Send webhook
    try:
        status_code, response = send_webhook(url, payload)
    except httpx.RequestError as e:
        print(f"Error: Request failed: {e}", file=sys.stderr)
        return 1

    # Report result
    if status_code in (200, 201, 202, 204):
        print(f"Success: HTTP {status_code}")
    else:
        print(f"Failed: HTTP {status_code}")
        if response:
            print(f"Response: {response}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
