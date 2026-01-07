# Mesh Connect + Anchor in a Box: Deposit Recipe

**Flow**: Exchange → Mesh → User's Stellar Wallet (non-custodial)

---

## Environment Setup

```bash
export MESH_CLIENT_ID="358ef0a7-9d16-4b55-966a-08ddde81b87e"
export MESH_SECRET="sk_sand_0yxjryt8.tsdg8qwcg4tn170a7rs37po9gq5cddvsnhpby8iijstkhs6e6fzfc9ztm9xebndy"
export MESH_API="https://sandbox-integration-api.meshconnect.com"
```

**Django settings.py**:
```python
MESH_CLIENT_ID = env("MESH_CLIENT_ID")
MESH_CLIENT_SECRET = env("MESH_CLIENT_SECRET")
MESH_API_URL = env("MESH_API_URL", default="https://sandbox-integration-api.meshconnect.com")
MESH_STELLAR_NETWORK_ID = "06855704-43d2-4ad2-a73c-372f0c3534e1"
```

---

## 1. Get Stellar Network ID (one-time lookup)

```bash
curl -s "$MESH_API/api/v1/transfers/managed/networks" \
  -H "X-Client-Id: $MESH_CLIENT_ID" \
  -H "X-Client-Secret: $MESH_SECRET" \
  | jq '.content.networks[] | select(.name == "Stellar") | {id, tokens: .supportedTokens, brokers: .supportedBrokerTypes}'
```

---

## 2. Create Link Token (Backend)

Called after SEP-10 auth. User's wallet address from JWT.

```bash
curl -s -X POST "$MESH_API/api/v1/linktoken" \
  -H "X-Client-Id: $MESH_CLIENT_ID" \
  -H "X-Client-Secret: $MESH_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "'"$SEP10_ACCOUNT_ID"'",
    "restrictMultipleAccounts": true,
    "transferOptions": {
      "transferType": "deposit",
      "transactionId": "'"$SEP24_TX_ID"'",
      "fundingOptions": {"enabled": true},
      "toAddresses": [
        {"symbol": "USDC", "address": "'"$USER_STELLAR_ADDRESS"'", "networkId": "06855704-43d2-4ad2-a73c-372f0c3534e1"},
        {"symbol": "EURC", "address": "'"$USER_STELLAR_ADDRESS"'", "networkId": "06855704-43d2-4ad2-a73c-372f0c3534e1"},
        {"symbol": "XLM", "address": "'"$USER_STELLAR_ADDRESS"'", "networkId": "06855704-43d2-4ad2-a73c-372f0c3534e1"}
      ]
    }
  }' | jq '{linkToken: .content.linkToken}'
```

---

## 3. Frontend: SEP-24 Interactive Page

Backend passes `link_token` and `mesh_client_id` to template context.

```html
<!-- templates/sep24/deposit.html -->
<div id="mesh-container"></div>
<script src="https://cdn.meshconnect.com/web-link-sdk/v1/link.js"></script>
<script>
const meshLink = createLink({
  clientId: "{{ mesh_client_id }}",
  onIntegrationConnected: (payload) => {
    console.log("Exchange connected:", payload.accessToken);
  },
  onTransferFinished: (payload) => {
    fetch("/sep24/mesh-callback/", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CSRFToken": "{{ csrf_token }}"},
      body: JSON.stringify({status: payload.status, txId: payload.transactionId})
    }).then(() => window.close());
  },
  onExit: (err) => console.log("User exited", err)
});
meshLink.openLink("{{ link_token }}");
</script>
```

---

## 4. Check Transfer Status (Backend Polling)

```bash
curl -s "$MESH_API/api/v1/transfers/managed/mesh?transactionId=$SEP24_TX_ID" \
  -H "X-Client-Id: $MESH_CLIENT_ID" \
  -H "X-Client-Secret: $MESH_SECRET" \
  | jq '.content | {status, symbol, amount, txHash: .networkTransactionId}'
```

---

## 5. Webhook Handler (DRF)

Configure webhook URL in Mesh Dashboard → Settings.

```python
# views.py
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from polaris.models import Transaction

class MeshWebhookView(APIView):
    """Receive Mesh transfer webhooks, verify via API poll, update SEP-24 tx."""
    
    def post(self, request):
        event_type = request.data.get("type")
        data = request.data.get("data", {})
        tx_id = data.get("transactionId")
        
        if event_type != "transfer.completed" or not tx_id:
            return Response(status=status.HTTP_200_OK)
        
        # Verify webhook data by polling Mesh API
        verified = self._verify_with_mesh(tx_id, data)
        if not verified:
            return Response({"error": "verification failed"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update Polaris transaction
        try:
            transaction = Transaction.objects.get(external_transaction_id=tx_id)
            if data.get("status") == "succeeded":
                transaction.status = Transaction.STATUS.pending_anchor
                transaction.external_extra = data.get("networkTransactionId")
                transaction.amount_in = data.get("amount")
            else:
                transaction.status = Transaction.STATUS.error
                transaction.status_message = f"Mesh transfer failed: {data.get('status')}"
            transaction.save()
        except Transaction.DoesNotExist:
            return Response({"error": "transaction not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(status=status.HTTP_200_OK)
    
    def _verify_with_mesh(self, tx_id: str, webhook_data: dict) -> bool:
        """Poll Mesh API to verify webhook payload matches actual transfer state."""
        resp = requests.get(
            f"{settings.MESH_API_URL}/api/v1/transfers/managed/mesh",
            params={"transactionId": tx_id},
            headers={
                "X-Client-Id": settings.MESH_CLIENT_ID,
                "X-Client-Secret": settings.MESH_CLIENT_SECRET,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return False
        
        mesh_data = resp.json().get("content", {})
        return (
            mesh_data.get("status") == webhook_data.get("status")
            and mesh_data.get("amount") == webhook_data.get("amount")
        )
```

```python
# urls.py
from django.urls import path
from .views import MeshWebhookView

urlpatterns = [
    path("webhooks/mesh/", MeshWebhookView.as_view(), name="mesh-webhook"),
]
```

**Verify webhook curl**:
```bash
curl -s "$MESH_API/api/v1/transfers/managed/mesh?transactionId=$TX_ID" \
  -H "X-Client-Id: $MESH_CLIENT_ID" \
  -H "X-Client-Secret: $MESH_SECRET" \
  | jq '{status, amount, networkTransactionId}'
```

---

## 6. Polaris Integration Points

### File: `integrations/deposit.py`

```python
from polaris.integrations import DepositIntegration
from polaris.models import Transaction
from django.conf import settings
import requests

class MeshDepositIntegration(DepositIntegration):
    
    def form_for_transaction(self, request, transaction, post_data=None, amount=None, *args, **kwargs):
        """Return None - we use Mesh Link UI instead of Polaris forms."""
        return None
    
    def content_for_template(self, template, form=None, transaction=None, *args, **kwargs):
        """Inject Mesh Link into SEP-24 interactive template."""
        if template.name != "deposit.html":
            return {}
        
        link_token = self._create_mesh_link_token(transaction)
        return {
            "link_token": link_token,
            "mesh_client_id": settings.MESH_CLIENT_ID,
        }
    
    def after_form_validation(self, form, transaction, *args, **kwargs):
        """Called after Mesh Link completes (via frontend callback)."""
        transaction.status = Transaction.STATUS.pending_external
        transaction.save()
    
    def _create_mesh_link_token(self, transaction: Transaction) -> str:
        resp = requests.post(
            f"{settings.MESH_API_URL}/api/v1/linktoken",
            headers={
                "X-Client-Id": settings.MESH_CLIENT_ID,
                "X-Client-Secret": settings.MESH_CLIENT_SECRET,
                "Content-Type": "application/json",
            },
            json={
                "userId": transaction.stellar_account,
                "restrictMultipleAccounts": True,
                "transferOptions": {
                    "transferType": "deposit",
                    "transactionId": str(transaction.id),
                    "fundingOptions": {"enabled": True},
                    "toAddresses": [
                        {"symbol": "USDC", "address": transaction.stellar_account, 
                         "networkId": settings.MESH_STELLAR_NETWORK_ID},
                        {"symbol": "EURC", "address": transaction.stellar_account,
                         "networkId": settings.MESH_STELLAR_NETWORK_ID},
                        {"symbol": "XLM", "address": transaction.stellar_account,
                         "networkId": settings.MESH_STELLAR_NETWORK_ID},
                    ],
                },
            },
            timeout=10,
        )
        return resp.json()["content"]["linkToken"]
```

### File: `integrations/rails.py`

```python
from polaris.integrations import RailsIntegration
from polaris.models import Transaction

class MeshRailsIntegration(RailsIntegration):
    
    def poll_pending_deposits(self, pending_deposits, *args, **kwargs):
        """
        For Mesh deposits, funds go directly to user wallet (non-custodial).
        This is called by: python manage.py poll_pending_deposits --loop
        
        Return transactions where Mesh transfer succeeded (webhook set status).
        """
        ready = []
        for tx in pending_deposits:
            if tx.status == Transaction.STATUS.pending_anchor:
                # Mesh already sent to user wallet - mark complete
                tx.amount_out = tx.amount_in  # No anchor fee for pass-through
                tx.amount_fee = 0
                tx.status = Transaction.STATUS.completed
                tx.save()
                ready.append(tx)
        return ready
```

### File: `integrations/__init__.py`

```python
from polaris.integrations import register_integrations
from .deposit import MeshDepositIntegration
from .rails import MeshRailsIntegration

register_integrations(
    deposit=MeshDepositIntegration(),
    rails=MeshRailsIntegration(),
)
```

---

## Polaris Transaction Status Flow

| Stage | Polaris Status | Trigger |
|-------|----------------|---------|
| User starts SEP-24 | `pending_user_transfer_start` | `/transactions/deposit/interactive` |
| Mesh Link opened | `pending_external` | `after_form_validation()` |
| Mesh webhook received | `pending_anchor` | `MeshWebhookView` |
| Polling confirms complete | `completed` | `poll_pending_deposits` |

---

## Key Notes

- **Non-custodial**: Funds go exchange → user wallet directly (anchor never touches funds)
- **SmartFunding**: `fundingOptions.enabled: true` auto-converts user's assets
- **Supported**: USDC, EURC, XLM on Stellar
- **Exchanges**: Coinbase, Binance, Kraken, Robinhood, etc.
- **Reconciliation**: Use `transaction.id` as Mesh `transactionId`
