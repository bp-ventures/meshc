#!/bin/bash
# End-to-End Mesh Connect Test Script
# Generated: 2026-01-06

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  Mesh Connect - End-to-End Test"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Configuration
TX_ID="test-20260106-165724"
WEBHOOK_URL=$(python3 -c "import local_settings; print(local_settings.MESH_WEBHOOK_URL)" 2>/dev/null || echo "https://webhook.site/your-unique-id")
MESH_URL="https://sandbox-web.meshconnect.com/b2b-iframe/358ef0a7-9d16-4b55-966a-08ddde81b87e/broker-connect?auth_code=OFVsgC1y_0is-6tkdcYhBiJGTYkBOD2tye042L3xxwrjfRm0VzJCESeUCXi_5Glq7ORM8v1Ws4efIykH9_HgaA&restrictMultipleAccounts=true&link_style=eyJwYyI6IiMwMzdGRkYiLCJwdCI6IiNGRkZGRkYiLCJzYyI6IiNGM0YzRjIiLCJzdCI6IiMwMDAwMDAiLCJiciI6MjQuMDAsImlyIjoyMy4wMCwiaW8iOjAuNjAwMDAwMDAsInQiOiJsb2dvIiwiaGMiOmZhbHNlLCJ0aCI6ImxpZ2h0In0%3d"

echo "📋 Test Details:"
echo "   Transaction ID: $TX_ID"
echo "   Webhook URL:    $WEBHOOK_URL"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 STEP 1: Open Mesh Connect UI in Browser"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Copy this URL and open it in your browser:"
echo ""
echo "  $MESH_URL"
echo ""
echo "Complete these steps in the browser:"
echo "  1. Select any exchange (Coinbase, Binance, Kraken, Gemini)"
echo "  2. Login with ANY credentials (e.g., user123 / pass123)"
echo "  3. Select an asset (USDC recommended)"
echo "  4. Review and confirm the 50.00 USDC transfer"
echo "  5. Wait for success confirmation"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Press ENTER after completing the browser flow..."
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 STEP 2: Verify Transfer Status via API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

source .venv/bin/activate 2>/dev/null || true

echo "Checking transfer status..."
echo ""

python -m meshc status "$TX_ID" --json 2>/dev/null || {
    echo "⚠️  Transfer not found yet. This is normal if:"
    echo "   - You haven't completed the browser flow yet"
    echo "   - The transfer is still processing"
    echo ""
    echo "Retrying in 5 seconds..."
    sleep 5
    python -m meshc status "$TX_ID" --json 2>/dev/null || echo "Still not found. Check browser."
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 STEP 3: Check Webhook Notification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
WEBHOOK_ID="${WEBHOOK_URL##*/}"
echo "Open your webhook.site dashboard:"
echo ""
echo "  https://webhook.site/#!/view/${WEBHOOK_ID}"
echo ""
echo "Look for a POST request with:"
echo "  • type: \"transfer.completed\""
echo "  • transactionId: \"$TX_ID\""
echo "  • status: \"succeeded\" or \"failed\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Test Complete!"
echo ""
echo "To check status anytime, run:"
echo "  meshc status $TX_ID"
echo ""
echo "═══════════════════════════════════════════════════════════"
