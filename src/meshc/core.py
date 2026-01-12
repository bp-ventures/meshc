"""Core library logic for Mesh Connect API.

Pure functions for API interaction. No printing, no CLI concerns.
"""
from __future__ import annotations

import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import SANDBOX_API_URL, SEPOLIA_NETWORK_ID, mask_secret
from .errors import ERROR_DESCRIPTIONS, get_error_description, is_retryable_error

logger = logging.getLogger("meshc")


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------


class MeshError(Exception):
    """Base exception for Mesh operations."""


class MeshAPIError(MeshError):
    """API request failed."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
        error_code: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}
        self.error_code = error_code or self._extract_error_code()

    def _extract_error_code(self) -> str | None:
        """Extract error code from response if present."""
        # Try common error code locations in Mesh responses
        if "errorCode" in self.response:
            return self.response["errorCode"]
        if "error" in self.response and isinstance(self.response["error"], dict):
            return self.response["error"].get("code")
        # Check if message matches a known error code
        msg = self.args[0] if self.args else ""
        for code in ERROR_DESCRIPTIONS:
            if code in msg:
                return code
        return None

    @property
    def description(self) -> str:
        """Get human-readable error description."""
        if self.error_code:
            return get_error_description(self.error_code)
        return str(self.args[0])

    @property
    def is_retryable(self) -> bool:
        """Check if this error might succeed on retry."""
        if self.error_code:
            return is_retryable_error(self.error_code)
        # Network errors are usually retryable
        return self.status_code in (429, 502, 503, 504) if self.status_code else False

    def __str__(self) -> str:
        parts = [self.args[0]]
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.status_code:
            parts.append(f"(status={self.status_code})")
        return " ".join(parts)


# -----------------------------------------------------------------------------
# Data Classes
# -----------------------------------------------------------------------------


@dataclass
class ToAddress:
    """Destination address for a transfer."""

    symbol: str  # e.g., "USDC", "XLM", "EURC"
    address: str  # Destination wallet address
    network_id: str  # Mesh network UUID
    amount: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "symbol": self.symbol,
            "address": self.address,
            "networkId": self.network_id,
        }
        if self.amount is not None:
            d["amount"] = self.amount
        return d


@dataclass
class TransferStatus:
    """Status of a Mesh transfer."""

    status: str  # "pending", "succeeded", "failed"
    amount: float | None = None
    symbol: str | None = None
    tx_hash: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return self.status in ("succeeded", "failed")

    @property
    def is_success(self) -> bool:
        return self.status == "succeeded"


@dataclass
class LinkToken:
    """Mesh link token for initiating transfers."""

    token: str
    expires_at: str | None = None
    pay_link: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Network:
    """Mesh supported network."""

    id: str
    name: str
    tokens: list[str] = field(default_factory=list)
    broker_types: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountToken:
    """Account token for reusing integrations (MMT).

    Mesh Managed Tokens allow skipping re-authentication by passing
    previously stored tokenIds to the Link SDK.
    """

    token_id: str  # Mesh-provided token ID
    integration_type: str  # "Coinbase", "Binance", "MetaMask", etc.

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for API payload."""
        return {
            "tokenId": self.token_id,
            "type": self.integration_type,
        }


# -----------------------------------------------------------------------------
# HTTP Client
# -----------------------------------------------------------------------------


def _request(
    method: str,
    url: str,
    client_id: str,
    client_secret: str,
    json: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Make authenticated request to Mesh API."""
    headers = {
        "X-Client-Id": client_id,
        "X-Client-Secret": client_secret,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    logger.debug(
        "%s %s (client=%s...)",
        method,
        url,
        client_id[:8] if client_id else "none",
    )

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.request(method, url, headers=headers, json=json, params=params)
    except httpx.RequestError as e:
        raise MeshAPIError(f"request failed: {e}") from e

    try:
        data = resp.json()
    except ValueError:
        data = {}

    if resp.status_code >= 400:
        msg = data.get("message") or data.get("error") or resp.text
        raise MeshAPIError(f"API error: {msg}", status_code=resp.status_code, response=data)

    return data


# -----------------------------------------------------------------------------
# API Functions
# -----------------------------------------------------------------------------


def create_link_token(
    client_id: str,
    client_secret: str,
    user_id: str,
    to_addresses: list[ToAddress] | list[dict[str, Any]],
    *,
    transfer_type: str = "deposit",
    transaction_id: str | None = None,
    enable_smart_funding: bool = True,
    integration_id: str | None = None,
    generate_pay_link: bool = False,
    restrict_multiple_accounts: bool = True,
    client_fee: float | None = None,
    amount_in_fiat: float | None = None,
    is_inclusive_fee_enabled: bool = False,
    account_tokens: list[AccountToken] | list[dict[str, Any]] | None = None,
    lang: str | None = None,
    api_url: str = SANDBOX_API_URL,
) -> LinkToken:
    """
    Create a Mesh link token for deposit/payment flow.

    Args:
        client_id: Mesh API client ID
        client_secret: Mesh API client secret
        user_id: Your application's user identifier
        to_addresses: List of destination addresses
        transfer_type: "deposit" or "payment"
        transaction_id: Your transaction ID for reconciliation
        enable_smart_funding: Auto-convert user's other tokens
        integration_id: Skip catalog, go directly to specific exchange
        generate_pay_link: Generate Mesh-hosted payment URL
        restrict_multiple_accounts: Limit to one account per user
        client_fee: Your fee as decimal (0.025 = 2.5%)
        amount_in_fiat: Amount in fiat (USD) instead of crypto
        is_inclusive_fee_enabled: Include fee in displayed amount
        account_tokens: Stored integration tokens for skipping re-auth (MMT)
        lang: UI language code (e.g., "en", "fr", "es", "de", "ja")

    Returns:
        LinkToken with token string and metadata

    Raises:
        MeshAPIError on failure
    """
    addresses = [
        addr.to_dict() if isinstance(addr, ToAddress) else addr
        for addr in to_addresses
    ]

    payload: dict[str, Any] = {
        "userId": user_id,
        "restrictMultipleAccounts": restrict_multiple_accounts,
        "transferOptions": {
            "transferType": transfer_type,
            "toAddresses": addresses,
            "fundingOptions": {"enabled": enable_smart_funding},
        },
    }

    if transaction_id:
        payload["transferOptions"]["transactionId"] = transaction_id
    if integration_id:
        payload["integrationId"] = integration_id
    if client_fee is not None:
        payload["transferOptions"]["clientFee"] = client_fee
    if amount_in_fiat is not None:
        payload["transferOptions"]["amountInFiat"] = amount_in_fiat
    if is_inclusive_fee_enabled:
        payload["transferOptions"]["isInclusiveFeeEnabled"] = True
    if generate_pay_link:
        payload["transferOptions"]["generatePayLink"] = True
    if account_tokens:
        # Convert AccountToken objects to dicts for API payload
        tokens = [
            tok.to_dict() if isinstance(tok, AccountToken) else tok
            for tok in account_tokens
        ]
        payload["accountTokens"] = tokens
        logger.debug("including %d stored tokens in payload", len(tokens))
        logger.debug("accountTokens payload: %s", tokens)
    if lang:
        payload["lang"] = lang

    url = f"{api_url.rstrip('/')}/api/v1/linktoken"
    logger.info("POST %s", url)
    logger.info("creating link token for user %s", user_id)
    logger.debug("full payload: %s", payload)

    data = _request("POST", url, client_id, client_secret, json=payload)
    content = data.get("content", {})

    return LinkToken(
        token=content.get("linkToken", ""),
        expires_at=content.get("expiresAt"),
        pay_link=content.get("payLink"),
        raw=content,
    )


def get_account_tokens_for_user(
    user_id: str | None = None,
    wallet_address: str | None = None,
    *,
    integration_type: str | None = None,
) -> list[AccountToken]:
    """Get stored account tokens for a user.

    Retrieves active tokens from storage for use with create_link_token().
    Allows users to skip re-authentication by reusing stored tokens.

    Args:
        user_id: Application user identifier
        wallet_address: Wallet public key
        integration_type: Optional filter for specific integration

    Returns:
        List of AccountToken instances for use with create_link_token()
        Returns empty list if storage not available or no tokens found

    Example:
        >>> tokens = get_account_tokens_for_user(user_id="user123")
        >>> result = create_link_token(..., account_tokens=tokens)
    """
    try:
        from .storage import list_tokens
    except ImportError:
        logger.warning("storage module not available")
        return []

    try:
        tokens = list_tokens(
            user_id=user_id,
            wallet_address=wallet_address,
            integration_type=integration_type,
            active_only=True,
        )
        logger.debug("found %d stored tokens", len(tokens))
        return [
            AccountToken(token_id=t.token_id, integration_type=t.integration_type)
            for t in tokens
        ]
    except Exception as e:
        logger.warning("failed to retrieve stored tokens: %s", e)
        return []


def get_transfer_status(
    client_id: str,
    client_secret: str,
    transaction_id: str,
    *,
    api_url: str = SANDBOX_API_URL,
) -> TransferStatus:
    """Get transfer status from Mesh API.

    Queries managed transfers endpoint. The transaction_id should be your
    clientTransactionId (e.g., bpv1767777617849) passed when creating the link token.

    Returns the first matching transfer, or unknown status if not found.
    """
    url = f"{api_url.rstrip('/')}/api/v1/transfers/managed/mesh"
    logger.debug("checking status for %s", transaction_id)

    # Query by clientTransactionId (our transaction ID passed during link creation)
    data = _request(
        "GET", url, client_id, client_secret,
        params={"clientTransactionId": transaction_id}
    )
    content = data.get("content", {})
    items = content.get("items", [])

    if not items:
        logger.debug("no transfers found for %s", transaction_id)
        return TransferStatus(
            status="not_found",
            raw=content,
        )

    # Return first matching transfer
    transfer = items[0]
    logger.debug("found transfer: %s", transfer.get("id"))

    return TransferStatus(
        status=transfer.get("status", "unknown"),
        amount=transfer.get("amount"),
        symbol=transfer.get("symbol"),
        tx_hash=transfer.get("hash"),
        raw=transfer,
    )


def get_networks(
    client_id: str,
    client_secret: str,
    *,
    api_url: str = SANDBOX_API_URL,
) -> list[Network]:
    """Fetch supported networks and tokens."""
    url = f"{api_url.rstrip('/')}/api/v1/transfers/managed/networks"
    logger.debug("fetching networks")

    data = _request("GET", url, client_id, client_secret)
    networks_data = data.get("content", {}).get("networks", [])

    networks = []
    for net in networks_data:
        # supportedTokens is already a list of symbol strings
        tokens = net.get("supportedTokens", [])
        networks.append(Network(
            id=net.get("id", ""),
            name=net.get("name", ""),
            tokens=tokens,
            broker_types=net.get("supportedBrokerTypes", []),
            raw=net,
        ))

    logger.info("found %d networks", len(networks))
    return networks


def get_stellar_network_id(
    client_id: str,
    client_secret: str,
    *,
    api_url: str = SANDBOX_API_URL,
) -> str:
    """Get the Stellar network ID. Raises MeshAPIError if not found."""
    networks = get_networks(client_id, client_secret, api_url=api_url)
    for net in networks:
        if net.name.lower() == "stellar":
            return net.id
    raise MeshAPIError("Stellar network not found")


# -----------------------------------------------------------------------------
# Mock/Simulation
# -----------------------------------------------------------------------------


def simulate_deposit(
    user_id: str,
    address: str,
    symbol: str,
    amount: float,
    *,
    network_id: str,
    client_id: str,
    client_secret: str,
    api_url: str = SANDBOX_API_URL,
    delay_seconds: float = 2.0,
    success_rate: float = 0.95,
) -> tuple[LinkToken, TransferStatus]:
    """
    Simulate a complete deposit flow for testing.

    Creates a real link token, then simulates the user interaction
    and transfer completion without actual funds moving.
    """
    tx_id = f"mock-{uuid.uuid4().hex[:12]}"
    logger.info("simulating deposit: %s %s to %s...", amount, symbol, address[:16])

    to_address = ToAddress(symbol=symbol, address=address, network_id=network_id, amount=amount)

    link_token = create_link_token(
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
        to_addresses=[to_address],
        transaction_id=tx_id,
        api_url=api_url,
    )

    logger.debug("simulating user interaction (%.1fs)", delay_seconds)
    time.sleep(delay_seconds)

    success = random.random() < success_rate

    if success:
        mock_hash = f"0x{uuid.uuid4().hex}"
        status = TransferStatus(
            status="succeeded",
            amount=amount,
            symbol=symbol,
            tx_hash=mock_hash,
            raw={"transactionId": tx_id, "status": "succeeded", "mock": True},
        )
        logger.info("mock deposit succeeded: %s", mock_hash)
    else:
        status = TransferStatus(
            status="failed",
            amount=amount,
            symbol=symbol,
            raw={"transactionId": tx_id, "status": "failed", "mock": True},
        )
        logger.info("mock deposit failed (simulated)")

    return link_token, status


# -----------------------------------------------------------------------------
# Sandbox Testing
# -----------------------------------------------------------------------------


def create_sandbox_cex_token(
    client_id: str,
    client_secret: str,
    user_id: str,
    to_address: str,
    symbol: str = "USDC",
    amount: float | None = None,
    *,
    network_id: str | None = None,
    transfer_type: str = "deposit",
    transaction_id: str | None = None,
    client_fee: float | None = None,
    enable_smart_funding: bool = True,
    lang: str | None = None,
    api_url: str = SANDBOX_API_URL,
) -> LinkToken:
    """
    Create a link token for sandbox CEX (exchange) testing.

    In sandbox mode, you can use any credentials (e.g., "user123"/"pass123")
    to authenticate with mocked exchanges like Coinbase or Binance.
    No real transactions occur—data is simulated.

    Args:
        client_id: Mesh sandbox API client ID
        client_secret: Mesh sandbox API client secret
        user_id: Your user identifier
        to_address: Destination wallet address
        symbol: Token symbol (default: USDC)
        amount: Optional transfer amount
        network_id: Network ID (defaults to Stellar)
        transfer_type: "deposit" or "payment" (default: deposit)
        transaction_id: Your transaction ID for reconciliation
        client_fee: Your fee as decimal (0.025 = 2.5%)
        enable_smart_funding: Auto-convert user's other tokens (default: True)
        lang: UI language code (e.g., "en", "fr", "es")
        api_url: Must be sandbox URL

    Returns:
        LinkToken to initialize the Link UI
    """
    from .config import DEFAULT_STELLAR_NETWORK_ID

    if "sandbox" not in api_url.lower():
        raise MeshError("CEX sandbox testing requires the sandbox API URL")

    addr = ToAddress(
        symbol=symbol,
        address=to_address,
        network_id=network_id or DEFAULT_STELLAR_NETWORK_ID,
        amount=amount,
    )

    logger.info("creating sandbox CEX token for user %s", user_id)
    return create_link_token(
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
        to_addresses=[addr],
        transfer_type=transfer_type,
        transaction_id=transaction_id,
        client_fee=client_fee,
        enable_smart_funding=enable_smart_funding,
        lang=lang,
        api_url=api_url,
    )


def create_sandbox_wallet_token(
    client_id: str,
    client_secret: str,
    user_id: str,
    to_address: str,
    symbol: str = "SEPOLIAETH",
    amount: float | None = None,
    *,
    api_url: str = SANDBOX_API_URL,
) -> LinkToken:
    """
    Create a link token for sandbox wallet (on-chain) testing.

    Uses Sepolia testnet for real on-chain transactions without real funds.
    You need Sepolia ETH from a faucet (e.g., https://cloud.google.com/application/web3/faucet/ethereum/sepolia).

    Supported wallets: MetaMask, Rainbow (on Sepolia testnet).

    Args:
        client_id: Mesh sandbox API client ID
        client_secret: Mesh sandbox API client secret
        user_id: Your user identifier
        to_address: Destination address (must be valid Ethereum address)
        symbol: Token symbol (default: SEPOLIAETH, also: PYUSD, USDG)
        amount: Optional transfer amount
        api_url: Must be sandbox URL

    Returns:
        LinkToken to initialize the Link UI
    """
    if "sandbox" not in api_url.lower():
        raise MeshError("Wallet sandbox testing requires the sandbox API URL")

    addr = ToAddress(
        symbol=symbol,
        address=to_address,
        network_id=SEPOLIA_NETWORK_ID,
        amount=amount,
    )

    logger.info("creating sandbox wallet token (Sepolia) for user %s", user_id)
    return create_link_token(
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
        to_addresses=[addr],
        api_url=api_url,
    )


def print_sandbox_instructions(test_type: str = "cex") -> str:
    """
    Return instructions for sandbox testing.

    Args:
        test_type: "cex" for exchange testing, "wallet" for on-chain testing
    """
    if test_type == "wallet":
        return """
SANDBOX WALLET TESTING (Sepolia Testnet)
=========================================
1. Get Sepolia ETH from: https://cloud.google.com/application/web3/faucet/ethereum/sepolia
2. Send test ETH to your MetaMask or Rainbow wallet
3. Use the link token to open Mesh Link UI
4. Select MetaMask or Rainbow and connect your wallet
5. Approve the on-chain transaction
6. Verify on Sepolia block explorer: https://sepolia.etherscan.io

Supported tokens: SEPOLIAETH, PYUSD, USDG
"""
    else:
        return """
SANDBOX CEX TESTING (Mocked Exchanges)
======================================
1. Use the link token to open Mesh Link UI
2. Select any exchange (Coinbase, Binance, etc.)
3. Enter ANY credentials (e.g., "user123" / "pass123")
4. Complete the mocked transfer flow
5. Check webhook for "succeeded" status

Note: All data is simulated. Prices are hardcoded.
Supported exchanges: All listed exchanges work in mock mode.
"""
