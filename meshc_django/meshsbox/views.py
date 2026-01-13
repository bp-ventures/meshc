"""Views for Mesh Connect sandbox frontend.

Two endpoints:
- GET /meshc/ - Self-service form
- POST /meshc/api/link-token/ - Generate link token
"""
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from meshc import create_sandbox_cex_token, create_sandbox_wallet_token, load_config


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
