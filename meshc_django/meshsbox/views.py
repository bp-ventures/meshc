"""Views for Mesh Connect sandbox frontend.

Endpoints:
- GET /meshc/ - Self-service form
- POST /meshc/api/link-token/ - Generate link token
- POST /meshc/api/webhook/ - Receive Mesh webhook events
"""
import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from meshc import create_sandbox_cex_token, create_sandbox_wallet_token, load_config

logger = logging.getLogger("meshsbox")


def get_client_ip(request) -> str:
    """Extract client IP, handling X-Forwarded-For from proxies."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def index(request):
    """Render the self-service form."""
    return render(request, 'meshsbox/link.html')


@csrf_exempt
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

    config = load_config()
    user_id = data.get('user_id', 'web-user')
    symbol = data.get('symbol', 'USDC')
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
