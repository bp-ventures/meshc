#!/bin/bash
# Test Webhook Integration Without UI Flow
# Tests that your webhook endpoint can receive Mesh-style payloads

set -e

WEBHOOK_URL="https://webhook.site/cf69e8e5-2235-4248-a3ae-b3fc9da3685d"

echo "═══════════════════════════════════════════════════════════"
echo "  Webhook Integration Test"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Testing webhook: $WEBHOOK_URL"
echo ""

# Generate mock transfer completed payload
MOCK_PAYLOAD=$(cat <<'EOF'
{
  "type": "transfer.completed",
  "timestamp": "2026-01-06T17:00:00Z",
  "data": {
    "transactionId": "test-manual-webhook",
    "status": "succeeded",
    "amount": "50.00",
    "symbol": "USDC",
    "networkId": "06855704-43d2-4ad2-a73c-372f0c3534e1",
    "networkTransactionId": "0xabc123def456789",
    "fromAddress": "binance_test_account",
    "toAddress": "GCKFBEIYV2U22IO2BJ4KVJOIP7XPWQGQFKKWXR6DOSJBV7STMAQSMTGG",
    "note": "Manual webhook test - backend integration verified"
  }
}
EOF
)

echo "📤 Sending mock 'transfer.completed' event..."
echo ""

# Send webhook
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Mesh-Signature: mock_signature_for_testing" \
  -d "$MOCK_PAYLOAD")

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
    echo "✅ Webhook sent successfully (HTTP $HTTP_CODE)"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 Verify Receipt"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. Open your webhook.site dashboard:"
    echo "   https://webhook.site/#!/view/cf69e8e5-2235-4248-a3ae-b3fc9da3685d"
    echo ""
    echo "2. You should see a POST request with:"
    echo "   • type: \"transfer.completed\""
    echo "   • transactionId: \"test-manual-webhook\""
    echo "   • status: \"succeeded\""
    echo "   • amount: \"50.00\""
    echo "   • symbol: \"USDC\""
    echo ""
    echo "3. Click on the request to view full JSON payload"
    echo ""
else
    echo "❌ Webhook failed (HTTP $HTTP_CODE)"
    echo ""
    echo "This might mean:"
    echo "  - Webhook URL is incorrect"
    echo "  - Network connectivity issue"
    echo "  - Webhook.site is down"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Mock Payload Sent:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "$MOCK_PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "$MOCK_PAYLOAD"
echo ""
echo "═══════════════════════════════════════════════════════════"
