"""Views for Mesh Connect sandbox frontend.

Endpoints:
- GET /meshc/ - Self-service form
- POST /meshc/api/link-token/ - Generate link token
- POST /meshc/api/save-token/ - Save integration token for Easy Relogin
- POST /meshc/api/webhook/ - Receive Mesh webhook events
"""
import json
import logging
import re
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from meshc import (
    create_sandbox_cex_token,
    create_sandbox_wallet_token,
    create_link_token,
    get_exchange_deposit_address,
    load_config,
    ToAddress,
)

logger = logging.getLogger("meshsbox")

# Address validation patterns
STELLAR_ADDRESS_RE = re.compile(r'^G[A-Z2-7]{55}$')
ETHEREUM_ADDRESS_RE = re.compile(r'^0x[a-fA-F0-9]{40}$')

# Symbols that use Ethereum addresses
ETHEREUM_SYMBOLS = {'SEPOLIAETH', 'ETH'}


def validate_address(address: str, symbol: str) -> str | None:
    """Validate wallet address format for the given symbol.

    Returns None if valid, error message if invalid.
    """
    if symbol in ETHEREUM_SYMBOLS:
        if not ETHEREUM_ADDRESS_RE.match(address):
            return f"Invalid Ethereum address format. Expected 0x followed by 40 hex characters."
    else:
        # Stellar address (XLM, USDC, etc.)
        if not STELLAR_ADDRESS_RE.match(address):
            return f"Invalid Stellar address format. Expected G followed by 55 base32 characters."
    return None


def get_client_ip(request) -> str:
    """Extract client IP from REMOTE_ADDR (don't trust spoofable XFF header)."""
    return request.META.get("REMOTE_ADDR", "")


def index(request):
    """Render the self-service form."""
    return render(request, 'meshsbox/link.html')


@require_POST
def api_link_token(request):
    """Generate Mesh link token.

    POST /meshc/api/link-token/
    {
        "address": "GBXY...",      # Required
        "symbol": "USDC",          # Default: USDC
        "amount": 100.0,           # Optional
        "wallet": false            # true for Sepolia wallet mode
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    address = data.get('address')
    if not address:
        return JsonResponse({'error': 'address is required'}, status=400)

    symbol = data.get('symbol', 'USDC')

    # Validate address format
    addr_error = validate_address(address, symbol)
    if addr_error:
        return JsonResponse({'error': addr_error}, status=400)

    config = load_config()
    user_id = data.get('user_id', 'web-user')
    amount = data.get('amount')
    wallet_mode = data.get('wallet', False)

    try:
        if wallet_mode:
            result = create_sandbox_wallet_token(
                client_id=config['client_id'],
                client_secret=config['client_secret'],
                user_id=user_id,
                to_address=address,
                symbol=symbol,
                amount=amount,
                api_url=config['api_url'],
            )
        else:
            result = create_sandbox_cex_token(
                client_id=config['client_id'],
                client_secret=config['client_secret'],
                user_id=user_id,
                to_address=address,
                symbol=symbol,
                amount=amount,
                api_url=config['api_url'],
            )

        return JsonResponse({
            'link_token': result.token,
            'expires_at': result.expires_at,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
def api_save_token(request):
    """Save integration token for Easy Relogin.

    POST /meshc/api/save-token/
    {
        "token_id": "tok_...",           # Required: Mesh access token
        "integration_type": "Coinbase",  # Required: broker name
        "user_id": "GBXY..."             # Required: stellar/wallet address
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    token_id = data.get('token_id')
    integration_type = data.get('integration_type')
    user_id = data.get('user_id')

    if not token_id or not integration_type or not user_id:
        return JsonResponse({'error': 'token_id, integration_type, and user_id are required'}, status=400)

    from .models import IntegrationToken

    token, created = IntegrationToken.objects.update_or_create(
        token_id=token_id,
        integration_type=integration_type,
        defaults={
            'user_id': user_id,
            'status': 'active',
            'scope': 'read',
            'lang': 'en',
        }
    )

    action = 'created' if created else 'updated'
    logger.info("save-token: %s token=%s type=%s user=%s", action, token_id[:12], integration_type, user_id[:12])

    return JsonResponse({'status': 'saved', 'action': action})


@csrf_exempt
@require_POST
def api_webhook(request):
    """Receive Mesh webhook events.

    POST /meshc/api/webhook/

    Stores one record per transaction_id. Multiple webhooks for same
    transaction append to history array. IP-filtered.

    Required fields: TransactionId, TransferStatus
    """
    # Check IP allowlist
    client_ip = get_client_ip(request)
    allowed_ips = getattr(settings, 'WEBHOOK_ALLOWED_IPS', ['127.0.0.1'])
    if client_ip not in allowed_ips:
        logger.warning("webhook: blocked ip=%s", client_ip)
        return JsonResponse({"error": "Forbidden"}, status=403)

    # Parse JSON body
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning("webhook: invalid JSON ip=%s", client_ip)
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Validate required fields
    transaction_id = payload.get("TransactionId")
    if not transaction_id:
        logger.warning("webhook: missing TransactionId")
        return JsonResponse({"error": "TransactionId required"}, status=400)

    status = payload.get("TransferStatus")
    if not status:
        logger.warning("webhook: missing TransferStatus tx=%s", transaction_id[:16])
        return JsonResponse({"error": "TransferStatus required"}, status=400)

    # Parse amount safely
    amount = None
    raw_amount = payload.get("SourceAmount") or payload.get("DestinationAmount")
    if raw_amount is not None:
        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError):
            logger.warning("webhook: invalid amount=%s tx=%s", raw_amount, transaction_id[:16])

    # Import model here to avoid circular imports during migrations
    from .models import MeshWebhook

    # Upsert: create or update
    webhook, created = MeshWebhook.objects.get_or_create(
        transaction_id=transaction_id,
        defaults={
            "status": status,
            "destination_address": payload.get("DestinationAddress", ""),
            "token": payload.get("Token", ""),
            "chain": payload.get("Chain", ""),
            "source_provider": payload.get("SourceAccountProvider", ""),
            "amount": amount,
            "tx_hash": payload.get("TxHash", ""),
            "history": [payload],
        }
    )

    if not created:
        # Update existing: append to history, update status
        webhook.history.append(payload)
        webhook.status = status
        webhook.tx_hash = payload.get("TxHash") or webhook.tx_hash
        if amount is not None:
            webhook.amount = amount
        webhook.save()
        logger.info("webhook: updated tx=%s status=%s count=%d", transaction_id[:16], status, len(webhook.history))
    else:
        logger.info("webhook: created tx=%s status=%s", transaction_id[:16], status)

    return JsonResponse({"status": "ok", "transaction_id": transaction_id})


def withdraw(request):
    """Render the withdraw form (wallet → exchange)."""
    return render(request, 'meshsbox/withdraw.html')


# Network IDs for withdraw flow (from meshc/config.py)
SEPOLIA_NETWORK_ID = "03b2d786-7092-4a6a-9737-d6013e21819b"  # Ethereum Sepolia testnet
STELLAR_NETWORK_ID = "06855704-43d2-4ad2-a73c-372f0c3534e1"

# Map symbols to network IDs (matches deposit template)
SYMBOL_NETWORK_MAP = {
    "XLM": STELLAR_NETWORK_ID,
    "USDC": STELLAR_NETWORK_ID,
    "SEPOLIAETH": SEPOLIA_NETWORK_ID,
}

# Standard test addresses (used throughout codebase for sandbox testing)
DEFAULT_STELLAR_ADDRESS = "GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX"
DEFAULT_SEPOLIA_ADDRESS = "0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c"

# Map network IDs to default test addresses
PLACEHOLDER_ADDRESSES = {
    SEPOLIA_NETWORK_ID: DEFAULT_SEPOLIA_ADDRESS,
    STELLAR_NETWORK_ID: DEFAULT_STELLAR_ADDRESS,
}


@require_POST
def api_withdraw_token(request):
    """Generate link token for wallet-to-exchange withdrawal.

    POST /meshc/api/withdraw-token/
    {
        "user_id": "GBXY...",       # Required: user identifier
        "exchange": "coinbase",      # Required: exchange type
        "symbol": "ETH",             # Required: token symbol
        "amount": 0.1,               # Optional: transfer amount
        "auth_token": "...",         # Optional: fresh token from exchange auth
        "mode": "transfer"           # Optional: "transfer" (default) or "auth"
    }

    Modes:
    - "transfer" (default): Create wallet link token for transfer
      - Uses stored token or auth_token from request
      - Returns {link_token, deposit_address, ...} or {needs_auth: true}
    - "auth": Create link token for exchange authentication only
      - Returns {link_token} for exchange connection
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_id = data.get('user_id')
    exchange = data.get('exchange')
    symbol = data.get('symbol')
    amount = data.get('amount')
    mode = data.get('mode', 'transfer')
    fresh_auth_token = data.get('auth_token')  # Token from recent exchange auth

    if not user_id:
        return JsonResponse({'error': 'user_id is required'}, status=400)
    if not exchange:
        return JsonResponse({'error': 'exchange is required'}, status=400)
    if not symbol:
        return JsonResponse({'error': 'symbol is required'}, status=400)

    # Map exchange names to Mesh API types
    exchange_type_map = {
        'coinbase': 'coinbase',
        'binanceInternational': 'binanceInternational',
        'binance': 'binanceInternational',
    }
    exchange_type = exchange_type_map.get(exchange, exchange)

    # Get network ID for the symbol
    network_id = SYMBOL_NETWORK_MAP.get(symbol.upper())
    if not network_id:
        return JsonResponse({'error': f'Unsupported symbol: {symbol}'}, status=400)

    # Exchange display names for DB lookup
    exchange_display_names = {
        'coinbase': 'Coinbase',
        'binanceInternational': 'Binance',
    }
    integration_type = exchange_display_names.get(exchange_type, exchange_type.title())

    config = load_config()

    # Mode: "auth" - Create link token for exchange authentication only
    if mode == 'auth':
        try:
            # Use a valid placeholder address that matches the network pattern
            placeholder_addr = PLACEHOLDER_ADDRESSES.get(network_id, "0x0000000000000000000000000000000000000000")
            result = create_link_token(
                client_id=config['client_id'],
                client_secret=config['client_secret'],
                user_id=user_id,
                to_addresses=[ToAddress(symbol=symbol, address=placeholder_addr, network_id=network_id)],
                transfer_type='deposit',
                api_url=config['api_url'],
            )
            logger.info("withdraw: created auth link token for %s on %s", user_id[:12], exchange_type)
            return JsonResponse({
                'link_token': result.token,
                'mode': 'auth',
                'expires_at': result.expires_at,
            })
        except Exception as e:
            logger.error("withdraw: failed to create auth token: %s", e)
            return JsonResponse({'error': str(e)}, status=500)

    # Mode: "transfer" - Create wallet link token for actual transfer
    # First, determine which auth token to use
    auth_token = fresh_auth_token  # Prefer fresh token from request

    if not auth_token:
        # Look up stored token from previous auth
        from .models import IntegrationToken
        try:
            stored_token = IntegrationToken.objects.filter(
                user_id=user_id,
                integration_type__iexact=integration_type,
                status='active'
            ).first()
            if stored_token:
                auth_token = stored_token.token_id
        except Exception as e:
            logger.error("withdraw: failed to query IntegrationToken: %s", e)
            return JsonResponse({'error': 'Database error'}, status=500)

    # If no auth token available, tell frontend to do exchange auth first
    if not auth_token:
        logger.info("withdraw: no auth token for %s on %s, needs_auth=true", user_id[:12], exchange_type)
        return JsonResponse({
            'needs_auth': True,
            'exchange': exchange,
            'integration_type': integration_type,
        })

    try:
        # Step 1: Get user's exchange deposit address
        deposit_addr = get_exchange_deposit_address(
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            auth_token=auth_token,
            symbol=symbol,
            network_id=network_id,
            exchange_type=exchange_type,
            api_url=config['api_url'],
        )

        logger.info("withdraw: got deposit address=%s for %s on %s", deposit_addr.address[:16], symbol, exchange_type)

        # Step 2: Create link token with toAddresses = exchange deposit address
        to_address = ToAddress(
            symbol=symbol,
            address=deposit_addr.address,
            network_id=network_id,
            amount=amount,
        )

        result = create_link_token(
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            user_id=user_id,
            to_addresses=[to_address],
            transfer_type='deposit',  # User is "depositing" to their exchange
            api_url=config['api_url'],
        )

        return JsonResponse({
            'link_token': result.token,
            'deposit_address': deposit_addr.address,
            'chain': deposit_addr.chain,
            'expires_at': result.expires_at,
        })

    except Exception as e:
        logger.error("withdraw: failed to create token: %s", e)
        error_msg = str(e)
        # If auth token is invalid/expired, tell frontend to re-auth
        if 'authToken' in error_msg.lower() or 'auth' in error_msg.lower() or 'unauthorized' in error_msg.lower():
            return JsonResponse({
                'needs_auth': True,
                'exchange': exchange,
                'integration_type': integration_type,
                'reason': 'token_expired',
            })
        return JsonResponse({'error': error_msg}, status=500)
