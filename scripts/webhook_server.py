#!/usr/bin/env python3
"""
Webhook proxy server - receives webhooks and forwards with status progression.

Simulates Mesh's behavior: receives a transfer webhook, then cycles through
statuses (Pending -> Succeeded) with delays, forwarding each to WEBHOOK_TARGET.

Usage:
    python scripts/webhook_server.py

Configure WEBHOOK_TARGET in local_settings.py.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# Add project root to path (where local_settings.py lives)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

PORT = 10587
DELAY_SECONDS = 5

# Status progression: current -> next
STATUS_NEXT = {
    "Pending": "Succeeded",
}


def load_target_url():
    """Load WEBHOOK_TARGET from local_settings.py."""
    try:
        import local_settings
        url = getattr(local_settings, "WEBHOOK_TARGET", None)
        if not url:
            print("ERROR: WEBHOOK_TARGET not set in local_settings.py", file=sys.stderr)
            sys.exit(1)
        return url
    except ImportError:
        print("ERROR: local_settings.py not found", file=sys.stderr)
        sys.exit(1)


def forward_webhook(url, payload):
    """Forward payload to target URL."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status
    except urllib.error.URLError as e:
        print(f"  ERROR forwarding: {e}", file=sys.stderr)
        return None


def process_webhook(payload, target_url):
    """Forward webhook with status progression."""
    status = payload.get("TransferStatus", "Pending")
    tx_id = payload.get("TransactionId", "unknown")

    print(f"  [{tx_id}] Received: {status}")

    # Wait before first forward
    print(f"  [{tx_id}] Waiting {DELAY_SECONDS}s...")
    time.sleep(DELAY_SECONDS)

    # Forward original status
    print(f"  [{tx_id}] Forwarding: {status}")
    forward_webhook(target_url, payload)

    # Progress through statuses
    while status in STATUS_NEXT:
        print(f"  [{tx_id}] Waiting {DELAY_SECONDS}s...")
        time.sleep(DELAY_SECONDS)

        status = STATUS_NEXT[status]
        payload["TransferStatus"] = status
        payload["SentTimestamp"] = int(time.time())

        print(f"  [{tx_id}] Forwarding: {status}")
        forward_webhook(target_url, payload)

    print(f"  [{tx_id}] Done")


class WebhookHandler(BaseHTTPRequestHandler):
    """Handle incoming webhook POST requests."""

    target_url = None  # Set at startup

    def do_POST(self):
        """Handle POST request."""
        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        # Respond 200 immediately
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK\n")

        # Process webhook (blocking - simple approach)
        process_webhook(payload, self.target_url)

    def log_message(self, format, *args):
        """Custom log format."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {args[0]}")


def main():
    """Start the webhook server."""
    target_url = load_target_url()

    print(f"Webhook proxy server")
    print(f"  Port: {PORT}")
    print(f"  Target: {target_url}")
    print(f"  Delay: {DELAY_SECONDS}s between status changes")
    print()

    WebhookHandler.target_url = target_url

    server = HTTPServer(("", PORT), WebhookHandler)
    print(f"Listening on http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
