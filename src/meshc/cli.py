"""CLI wrapper for meshc.

Thin adapter: parses args, calls core library, formats output.
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import pathlib
import random
import sys
import time
import webbrowser
from typing import Any

from .config import MeshConfigError, load_config
from .core import (
    AccountToken,
    MeshAPIError,
    ToAddress,
    create_link_token,
    create_sandbox_cex_token,
    create_sandbox_wallet_token,
    get_account_tokens_for_user,
    get_networks,
    get_transfer_status,
    print_sandbox_instructions,
    simulate_deposit,
)
from .errors import get_error_description

logger = logging.getLogger("meshc")


def _setup_logging(verbose: bool = False, debug: bool = False) -> None:
    level = logging.WARNING
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def _output(data: Any, as_json: bool = False) -> None:
    """Write output to stdout."""
    if as_json:
        print(json.dumps(data, indent=2, default=str))
    elif isinstance(data, str):
        print(data)
    elif isinstance(data, dict):
        for k, v in data.items():
            print(f"{k}: {v}")
    elif isinstance(data, list):
        for item in data:
            print(item)


def _error(msg: str) -> None:
    """Write error to stderr."""
    print(f"Error: {msg}", file=sys.stderr)


def _decode_link_token(token: str) -> str:
    """Decode a base64-encoded link token to get the actual URL."""
    try:
        return base64.b64decode(token).decode('utf-8')
    except Exception as e:
        logger.warning(f"failed to decode link token: {e}")
        return token


def _generate_transaction_id() -> str:
    """Generate a unique transaction ID: bpv + timestamp + 3 random digits."""
    timestamp = int(time.time())
    rand = random.randint(100, 999)
    return f"bpv{timestamp}{rand}"


# -----------------------------------------------------------------------------
# Subcommands
# -----------------------------------------------------------------------------


def cmd_link_token(args: argparse.Namespace) -> int:
    """Create a Mesh link token."""
    try:
        config = load_config()
    except MeshConfigError as e:
        _error(str(e))
        return 1

    to_address = ToAddress(
        symbol=args.symbol,
        address=args.address,
        network_id=args.network_id or config["stellar_network_id"],
        amount=args.amount,
    )

    # Load stored tokens if requested
    account_tokens = None
    if getattr(args, "use_stored_tokens", False):
        try:
            from .config import init_token_storage
            init_token_storage()
            account_tokens = get_account_tokens_for_user(user_id=args.user_id)
            if account_tokens:
                logger.info("found %d stored token(s) for user %s", len(account_tokens), args.user_id)
        except Exception as e:
            logger.warning("failed to load stored tokens: %s", e)

    try:
        result = create_link_token(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            user_id=args.user_id,
            to_addresses=[to_address],
            transfer_type=args.transfer_type,
            transaction_id=args.transaction_id,
            enable_smart_funding=getattr(args, "smart_funding", True),
            integration_id=args.integration_id,
            client_fee=getattr(args, "client_fee", None),
            amount_in_fiat=getattr(args, "amount_in_fiat", None),
            is_inclusive_fee_enabled=getattr(args, "inclusive_fee", False),
            account_tokens=account_tokens,
            api_url=config["api_url"],
        )
    except MeshAPIError as e:
        _error(str(e))
        return 1

    if args.json:
        _output(result.raw, as_json=True)
    else:
        print(result.token)

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Check transfer status."""
    try:
        config = load_config()
    except MeshConfigError as e:
        _error(str(e))
        return 1

    def fetch_status():
        return get_transfer_status(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            transaction_id=args.transaction_id,
            api_url=config["api_url"],
        )

    try:
        if args.poll:
            while True:
                status = fetch_status()
                if args.json:
                    _output(status.raw, as_json=True)
                else:
                    print(f"status: {status.status}", file=sys.stderr)

                if status.is_complete:
                    break
                time.sleep(args.interval)
        else:
            status = fetch_status()

        if args.json:
            _output(status.raw, as_json=True)
        else:
            _output({
                "status": status.status,
                "amount": status.amount,
                "symbol": status.symbol,
                "tx_hash": status.tx_hash,
            })

        return 0 if status.is_success else 1

    except MeshAPIError as e:
        _error(str(e))
        return 1


def cmd_networks(args: argparse.Namespace) -> int:
    """List supported networks."""
    try:
        config = load_config()
    except MeshConfigError as e:
        _error(str(e))
        return 1

    try:
        networks = get_networks(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            api_url=config["api_url"],
        )
    except MeshAPIError as e:
        _error(str(e))
        return 1

    if args.filter:
        networks = [n for n in networks if args.filter.lower() in n.name.lower()]

    if args.json:
        _output([n.raw for n in networks], as_json=True)
    else:
        for net in networks:
            tokens = ", ".join(net.tokens[:5])
            if len(net.tokens) > 5:
                tokens += f" (+{len(net.tokens) - 5} more)"
            print(f"{net.id}  {net.name:20}  {tokens}")

    return 0


def cmd_mock_deposit(args: argparse.Namespace) -> int:
    """Simulate a deposit flow."""
    try:
        config = load_config()
    except MeshConfigError as e:
        _error(str(e))
        return 1

    try:
        link_token, status = simulate_deposit(
            user_id=args.user_id,
            address=args.address,
            symbol=args.symbol,
            amount=args.amount,
            network_id=args.network_id or config["stellar_network_id"],
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            api_url=config["api_url"],
            delay_seconds=args.delay,
        )
    except MeshAPIError as e:
        _error(str(e))
        return 1

    if args.json:
        _output({
            "link_token": link_token.token,
            "status": status.raw,
        }, as_json=True)
    else:
        print(f"Link token: {link_token.token[:40]}...")
        print(f"Status: {status.status}")
        if status.tx_hash:
            print(f"TX Hash: {status.tx_hash}")

    return 0 if status.is_success else 1


def cmd_sandbox_cex(args: argparse.Namespace) -> int:
    """Test CEX (exchange) or wallet flow in sandbox."""
    try:
        config = load_config()
    except MeshConfigError as e:
        _error(str(e))
        return 1

    wallet_mode = getattr(args, 'wallet', False)

    # Print instructions if requested
    if args.instructions:
        print(print_sandbox_instructions("wallet" if wallet_mode else "cex"))
        return 0

    # Wallet mode validation
    default_stellar_address = "GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX"
    if wallet_mode and (not args.address or args.address == default_stellar_address):
        _error("--wallet mode requires --address with an Ethereum address (0x...)")
        return 1

    # Generate transaction ID if not provided (CEX mode only)
    transaction_id = getattr(args, 'transaction_id', None) or _generate_transaction_id()

    try:
        if wallet_mode:
            # Wallet mode: Sepolia testnet
            symbol = args.symbol if args.symbol != "USDC" else "SEPOLIAETH"
            result = create_sandbox_wallet_token(
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                user_id=args.user_id,
                to_address=args.address,
                symbol=symbol,
                amount=args.amount,
                api_url=config["api_url"],
            )
        else:
            # CEX mode: Stellar testnet (default)
            result = create_sandbox_cex_token(
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                user_id=args.user_id,
                to_address=args.address,
                symbol=args.symbol,
                amount=args.amount,
                network_id=getattr(args, 'network_id', None),
                transfer_type=getattr(args, 'transfer_type', 'deposit'),
                transaction_id=transaction_id,
                client_fee=getattr(args, 'client_fee', None),
                enable_smart_funding=getattr(args, 'smart_funding', True),
                lang=getattr(args, 'lang', None),
                api_url=config["api_url"],
            )
    except MeshAPIError as e:
        _error(str(e))
        if e.error_code:
            print(f"  Hint: {get_error_description(e.error_code)}", file=sys.stderr)
        return 1

    if args.json:
        output = result.raw.copy()
        if not wallet_mode:
            output["transactionId"] = transaction_id
        _output(output, as_json=True)
    else:
        url = _decode_link_token(result.token)

        if wallet_mode:
            print("SANDBOX WALLET TEST (Sepolia Testnet)")
            print("=" * 40)
            print(f"Link URL: {url}")
            print()
            print("Prerequisites:")
            print("1. Get Sepolia ETH: https://cloud.google.com/application/web3/faucet/ethereum/sepolia")
            print("2. Send to your MetaMask/Rainbow wallet")
            print()
            print("Next steps:")
            print("1. Select MetaMask or Rainbow")
            print("2. Approve the on-chain transaction")
            print("3. Verify at: https://sepolia.etherscan.io")
        else:
            print("SANDBOX CEX TEST")
            print("=" * 40)
            print(f"Transaction ID: {transaction_id}")
            print(f"Link URL: {url}")
            print()
            print("Next steps:")
            print("1. Select any exchange (Coinbase, Binance, etc.)")
            print("2. Use credentials displayed (e.g., MeshUser/rPpass123)")
            print("3. Complete the mocked transfer flow")
            print()
            print(f"Check status: meshc status {transaction_id}")

        if getattr(args, 'open', False):
            print()
            print("Opening in browser...")
            webbrowser.open(url)

    return 0


def cmd_errors(args: argparse.Namespace) -> int:
    """List known error codes and descriptions."""
    from .errors import ERROR_DESCRIPTIONS

    if args.code:
        desc = get_error_description(args.code)
        print(f"{args.code}: {desc}")
    else:
        for code, desc in sorted(ERROR_DESCRIPTIONS.items()):
            print(f"{code:40} {desc[:60]}")

    return 0


def cmd_token_store(args: argparse.Namespace) -> int:
    """Store an integration token."""
    try:
        from .config import init_token_storage
        from .storage import store_token
    except ImportError as e:
        _error(f"storage module not available: {e}")
        return 1

    # Initialize token storage on first use
    try:
        init_token_storage()
    except Exception as e:
        _error(f"failed to initialize token storage: {e}")
        return 1

    # Parse metadata JSON if provided
    metadata = {}
    if args.metadata:
        try:
            metadata = json.loads(args.metadata)
        except json.JSONDecodeError as e:
            _error(f"invalid metadata JSON: {e}")
            return 1

    try:
        token = store_token(
            token_id=args.token_id,
            integration_type=args.integration_type,
            user_id=args.user_id,
            wallet_address=args.wallet_address,
            scope=args.scope or "read",
            lang=getattr(args, "lang", "en"),
            expires_at=args.expires_at,
            metadata=metadata,
        )

        if args.json:
            _output(token.to_dict(), as_json=True)
        else:
            print(f"stored token: {token.token_id[:12]}... ({token.integration_type})")
            if token.user_id:
                print(f"  user_id: {token.user_id}")
            if token.wallet_address:
                print(f"  wallet: {token.wallet_address[:10]}...")
            print(f"  scope: {token.scope}")
            if token.lang:
                print(f"  lang: {token.lang}")
            print(f"  status: {token.status}")

        return 0

    except Exception as e:
        _error(f"failed to store token: {e}")
        return 1


def cmd_token_list(args: argparse.Namespace) -> int:
    """List stored tokens."""
    try:
        from .config import init_token_storage
        from .storage import list_tokens
    except ImportError as e:
        _error(f"storage module not available: {e}")
        return 1

    try:
        init_token_storage()
    except Exception as e:
        _error(f"failed to initialize token storage: {e}")
        return 1

    try:
        tokens = list_tokens(
            user_id=args.user_id,
            wallet_address=args.wallet_address,
            integration_type=args.integration_type,
            active_only=args.active_only,
        )

        if args.json:
            _output([t.to_dict() for t in tokens], as_json=True)
        else:
            if not tokens:
                print("no tokens found")
                return 0

            # Table output
            print(f"{'Token ID':<30} {'Type':<15} {'User/Wallet':<25} {'Scope':<6} {'Lang':<5} {'Status':<8}")
            print("=" * 95)
            for token in tokens:
                token_id = token.token_id[:28] + ".." if len(token.token_id) > 28 else token.token_id
                user_or_wallet = token.user_id or (token.wallet_address[:23] + ".." if token.wallet_address and len(token.wallet_address) > 23 else token.wallet_address or "")
                lang = token.lang or "en"
                print(f"{token_id:<30} {token.integration_type:<15} {user_or_wallet:<25} {token.scope:<6} {lang:<5} {token.status:<8}")

            print(f"\nTotal: {len(tokens)} token(s)")

        return 0

    except Exception as e:
        _error(f"failed to list tokens: {e}")
        return 1


def cmd_token_get(args: argparse.Namespace) -> int:
    """Get a specific token."""
    try:
        from .config import init_token_storage
        from .storage import get_token
    except ImportError as e:
        _error(f"storage module not available: {e}")
        return 1

    try:
        init_token_storage()
    except Exception as e:
        _error(f"failed to initialize token storage: {e}")
        return 1

    try:
        token = get_token(
            token_id=args.token_id,
            integration_type=args.integration_type,
        )

        if not token:
            _error("token not found")
            return 1

        if args.json:
            _output(token.to_dict(), as_json=True)
        else:
            print(f"Token ID: {token.token_id}")
            print(f"Integration: {token.integration_type}")
            if token.user_id:
                print(f"User ID: {token.user_id}")
            if token.wallet_address:
                print(f"Wallet: {token.wallet_address}")
            print(f"Scope: {token.scope}")
            print(f"Status: {token.status}")
            if token.lang:
                print(f"Language: {token.lang}")
            print(f"Created: {token.created_at}")
            print(f"Updated: {token.updated_at}")
            if token.expires_at:
                print(f"Expires: {token.expires_at}")
            if token.metadata:
                print(f"Metadata: {json.dumps(token.metadata, indent=2)}")

        return 0

    except Exception as e:
        _error(f"failed to get token: {e}")
        return 1


def cmd_token_revoke(args: argparse.Namespace) -> int:
    """Revoke a token."""
    try:
        from .config import init_token_storage
        from .storage import revoke_token
    except ImportError as e:
        _error(f"storage module not available: {e}")
        return 1

    try:
        init_token_storage()
    except Exception as e:
        _error(f"failed to initialize token storage: {e}")
        return 1

    try:
        success = revoke_token(
            token_id=args.token_id,
            integration_type=args.integration_type,
        )

        if success:
            print(f"revoked token: {args.token_id[:12]}...")
            return 0
        else:
            _error("token not found")
            return 1

    except Exception as e:
        _error(f"failed to revoke token: {e}")
        return 1


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="meshc",
        description="Mesh Connect deposit flow CLI",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--debug", action="store_true", help="Debug output")
    parser.add_argument("--json", action="store_true", help="JSON output")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # Common args for all subcommands
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="JSON output")

    # link-token
    p_link = subparsers.add_parser("link-token", parents=[common], help="Create a link token")
    p_link.add_argument("--user-id", required=True, help="User identifier")
    p_link.add_argument("--address", required=True, help="Destination wallet address")
    p_link.add_argument("--symbol", required=True, help="Token symbol (USDC, XLM, etc.)")
    p_link.add_argument("--amount", type=float, help="Transfer amount")
    p_link.add_argument("--network-id", help="Network ID (defaults to Stellar)")
    p_link.add_argument("--transfer-type", default="deposit", help="deposit or payment")
    p_link.add_argument("--transaction-id", help="Your transaction ID")
    p_link.add_argument("--integration-id", help="Go directly to specific exchange")
    p_link.add_argument("--client-fee", type=float, help="Your fee as decimal (0.025 = 2.5%%)")
    p_link.add_argument("--amount-in-fiat", type=float, help="Amount in USD (converts to crypto)")
    p_link.add_argument("--inclusive-fee", action="store_true", help="Include fee in displayed amount")
    p_link.add_argument("--use-stored-tokens", action="store_true", help="Use stored tokens to skip re-auth")
    p_link.add_argument("--smart-funding", dest="smart_funding", action="store_true",
                        default=True, help="Enable SmartFunding (default)")
    p_link.add_argument("--no-smart-funding", dest="smart_funding", action="store_false",
                        help="Disable SmartFunding")
    p_link.set_defaults(func=cmd_link_token)

    # status
    p_status = subparsers.add_parser("status", parents=[common], help="Check transfer status")
    p_status.add_argument("transaction_id", help="Transaction ID to check")
    p_status.add_argument("--poll", action="store_true", help="Poll until complete")
    p_status.add_argument("--interval", type=float, default=5.0, help="Poll interval (seconds)")
    p_status.set_defaults(func=cmd_status)

    # networks
    p_nets = subparsers.add_parser("networks", parents=[common], help="List supported networks")
    p_nets.add_argument("--filter", help="Filter by name")
    p_nets.set_defaults(func=cmd_networks)

    # mock-deposit
    p_mock = subparsers.add_parser("mock-deposit", parents=[common], help="Simulate a deposit")
    p_mock.add_argument("--user-id", required=True, help="User identifier")
    p_mock.add_argument("--address", required=True, help="Destination wallet address")
    p_mock.add_argument("--symbol", required=True, help="Token symbol")
    p_mock.add_argument("--amount", type=float, required=True, help="Amount")
    p_mock.add_argument("--network-id", help="Network ID (defaults to Stellar)")
    p_mock.add_argument("--delay", type=float, default=2.0, help="Simulated delay")
    p_mock.set_defaults(func=cmd_mock_deposit)

    # sandbox-cex (also supports --wallet for Sepolia testnet)
    p_cex = subparsers.add_parser(
        "sandbox-cex", parents=[common],
        help="Test CEX (exchange) or wallet flow in sandbox"
    )
    p_cex.add_argument("--user-id", default="test-user", help="User ID (default: test-user)")
    p_cex.add_argument("--address", default="GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX",
                       help="Destination address (default: test Stellar address)")
    p_cex.add_argument("--symbol", default="USDC", help="Token (default: USDC, or SEPOLIAETH for --wallet)")
    p_cex.add_argument("--amount", type=float, help="Amount")
    p_cex.add_argument("--network-id", help="Network ID (default: Stellar)")
    p_cex.add_argument("--transfer-type", default="deposit", help="Transfer type: deposit or payment")
    p_cex.add_argument("--transaction-id", help="Your transaction ID (auto-generated if not provided)")
    p_cex.add_argument("--client-fee", type=float, help="Your fee as decimal (0.025 = 2.5%%)")
    p_cex.add_argument("--smart-funding", dest="smart_funding", action="store_true", default=True,
                       help="Enable SmartFunding (default: enabled)")
    p_cex.add_argument("--no-smart-funding", dest="smart_funding", action="store_false",
                       help="Disable SmartFunding")
    p_cex.add_argument("--lang", help="UI language code (en, fr, es, de, ja)")
    p_cex.add_argument("--wallet", action="store_true",
                       help="Use wallet mode (Sepolia testnet) instead of CEX")
    p_cex.add_argument("--instructions", action="store_true", help="Show testing instructions")
    p_cex.add_argument("--open", action="store_true", help="Automatically open URL in browser")
    p_cex.set_defaults(func=cmd_sandbox_cex)

    # errors
    p_errors = subparsers.add_parser("errors", help="List known error codes")
    p_errors.add_argument("code", nargs="?", help="Specific error code to look up")
    p_errors.set_defaults(func=cmd_errors)

    # token-store
    p_token_store = subparsers.add_parser(
        "token-store", parents=[common],
        help="Store an integration token for reuse"
    )
    p_token_store.add_argument("--token-id", required=True, help="Mesh token ID")
    p_token_store.add_argument("--integration-type", required=True, help="Integration type (Coinbase, Binance, etc.)")
    p_token_store.add_argument("--user-id", help="User identifier")
    p_token_store.add_argument("--wallet-address", help="Wallet public key")
    p_token_store.add_argument("--scope", choices=["read", "write"], help="Token scope (default: read)")
    p_token_store.add_argument("--lang", help="User language code (default: en). Examples: en, fr, es, de, ja")
    p_token_store.add_argument("--expires-at", help="Expiration timestamp (ISO 8601)")
    p_token_store.add_argument("--metadata", help="Additional metadata as JSON string")
    p_token_store.set_defaults(func=cmd_token_store)

    # token-list
    p_token_list = subparsers.add_parser(
        "token-list", parents=[common],
        help="List stored integration tokens"
    )
    p_token_list.add_argument("--user-id", help="Filter by user ID")
    p_token_list.add_argument("--wallet-address", help="Filter by wallet address")
    p_token_list.add_argument("--integration-type", help="Filter by integration type")
    p_token_list.add_argument("--active-only", action="store_true", help="Only show active tokens")
    p_token_list.set_defaults(func=cmd_token_list)

    # token-get
    p_token_get = subparsers.add_parser(
        "token-get", parents=[common],
        help="Get details of a specific token"
    )
    p_token_get.add_argument("token_id", help="Token ID to retrieve")
    p_token_get.add_argument("--integration-type", help="Filter by integration type")
    p_token_get.set_defaults(func=cmd_token_get)

    # token-revoke
    p_token_revoke = subparsers.add_parser(
        "token-revoke", parents=[common],
        help="Revoke a stored token"
    )
    p_token_revoke.add_argument("token_id", help="Token ID to revoke")
    p_token_revoke.add_argument("--integration-type", help="Filter by integration type")
    p_token_revoke.set_defaults(func=cmd_token_revoke)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    _setup_logging(args.verbose, args.debug)

    if not args.command:
        parser.print_help()
        return 2

    # Pass json flag to subcommand
    if hasattr(args, "func"):
        return args.func(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
