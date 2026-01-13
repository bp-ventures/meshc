"""Tests for meshsbox Django app."""
import json
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase, TestCase, Client, override_settings


class IndexViewTests(SimpleTestCase):
    """Tests for the index view."""

    def setUp(self):
        self.client = Client()

    def test_renders(self):
        """Index page loads successfully."""
        response = self.client.get('/meshc/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mesh Connect')


class ApiLinkTokenTests(SimpleTestCase):
    """Tests for the link token API endpoint."""

    def setUp(self):
        self.client = Client()

    def test_requires_post(self):
        """API rejects GET requests."""
        response = self.client.get('/meshc/api/link-token/')
        self.assertEqual(response.status_code, 405)

    def test_requires_json(self):
        """API rejects non-JSON body."""
        response = self.client.post('/meshc/api/link-token/', data='bad', content_type='text/plain')
        self.assertEqual(response.status_code, 400)

    def test_requires_address(self):
        """API requires address field."""
        response = self.client.post('/meshc/api/link-token/',
            data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('address', response.json()['error'])

    @patch('meshsbox.views.create_sandbox_cex_token')
    @patch('meshsbox.views.load_config')
    def test_cex_success(self, mock_config, mock_create):
        """API generates CEX token successfully."""
        mock_config.return_value = {'client_id': 'x', 'client_secret': 'x', 'api_url': 'x'}
        mock_create.return_value = MagicMock(token='tok', expires_at='2025-01-01')

        response = self.client.post('/meshc/api/link-token/',
            data=json.dumps({'address': 'GTEST'}), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['link_token'], 'tok')

    @patch('meshsbox.views.create_sandbox_wallet_token')
    @patch('meshsbox.views.load_config')
    def test_wallet_mode(self, mock_config, mock_create):
        """API generates wallet token when wallet=true."""
        mock_config.return_value = {'client_id': 'x', 'client_secret': 'x', 'api_url': 'x'}
        mock_create.return_value = MagicMock(token='wtok', expires_at='2025-01-01')

        response = self.client.post('/meshc/api/link-token/',
            data=json.dumps({'address': '0xABC', 'wallet': True}), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        mock_create.assert_called_once()


@override_settings(WEBHOOK_ALLOWED_IPS=['127.0.0.1'])
class WebhookApiTests(TestCase):
    """Tests for webhook endpoint."""

    def setUp(self):
        self.client = Client()

    def test_requires_post(self):
        """GET should be rejected."""
        response = self.client.get('/meshc/api/webhook/')
        self.assertEqual(response.status_code, 405)

    def test_requires_json(self):
        """Non-JSON body rejected."""
        response = self.client.post('/meshc/api/webhook/', data='not json', content_type='text/plain')
        self.assertEqual(response.status_code, 400)

    def test_requires_transaction_id(self):
        """Missing TransactionId rejected."""
        response = self.client.post('/meshc/api/webhook/',
            data=json.dumps({"TransferStatus": "Pending"}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("TransactionId", response.json()["error"])

    def test_requires_transfer_status(self):
        """Missing TransferStatus rejected."""
        response = self.client.post('/meshc/api/webhook/',
            data=json.dumps({"TransactionId": "bpv123"}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("TransferStatus", response.json()["error"])

    def test_creates_webhook_record(self):
        """First webhook creates record."""
        payload = {
            "TransactionId": "bpv123456",
            "TransferStatus": "Pending",
            "Token": "USDC",
            "Chain": "Stellar",
            "DestinationAddress": "GBXYTEST...",
            "SourceAccountProvider": "Coinbase",
            "SourceAmount": 50.0,
        }
        response = self.client.post('/meshc/api/webhook/',
            data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 200)

        from meshsbox.models import MeshWebhook
        webhook = MeshWebhook.objects.get(transaction_id="bpv123456")
        self.assertEqual(webhook.status, "Pending")
        self.assertEqual(webhook.token, "USDC")
        self.assertEqual(len(webhook.history), 1)

    def test_appends_to_existing_record(self):
        """Second webhook updates existing record."""
        tx_id = "bpv999888"

        # First webhook: Pending
        self.client.post('/meshc/api/webhook/',
            data=json.dumps({"TransactionId": tx_id, "TransferStatus": "Pending", "Token": "ETH"}),
            content_type='application/json')

        # Second webhook: Succeeded with TxHash
        self.client.post('/meshc/api/webhook/',
            data=json.dumps({"TransactionId": tx_id, "TransferStatus": "Succeeded", "Token": "ETH", "TxHash": "0xabc123"}),
            content_type='application/json')

        from meshsbox.models import MeshWebhook
        webhook = MeshWebhook.objects.get(transaction_id=tx_id)

        self.assertEqual(webhook.status, "Succeeded")  # Updated
        self.assertEqual(webhook.tx_hash, "0xabc123")  # Updated
        self.assertEqual(len(webhook.history), 2)  # Appended
        self.assertEqual(webhook.history[0]["TransferStatus"], "Pending")
        self.assertEqual(webhook.history[1]["TransferStatus"], "Succeeded")

    @override_settings(WEBHOOK_ALLOWED_IPS=['10.0.0.1'])
    def test_ip_filter_blocks_unauthorized(self):
        """Requests from non-allowed IPs are blocked."""
        response = self.client.post('/meshc/api/webhook/',
            data=json.dumps({"TransactionId": "bpv111", "TransferStatus": "Pending"}),
            content_type='application/json')
        self.assertEqual(response.status_code, 403)
