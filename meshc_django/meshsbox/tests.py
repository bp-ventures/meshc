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

    def test_rejects_invalid_stellar_address(self):
        """API rejects invalid Stellar address format."""
        response = self.client.post('/meshc/api/link-token/',
            data=json.dumps({'address': 'invalid', 'symbol': 'USDC'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Stellar', response.json()['error'])

    def test_rejects_invalid_ethereum_address(self):
        """API rejects invalid Ethereum address format."""
        response = self.client.post('/meshc/api/link-token/',
            data=json.dumps({'address': 'notanaddress', 'symbol': 'SEPOLIAETH'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Ethereum', response.json()['error'])

    def test_rejects_sql_injection_attempt(self):
        """API rejects malicious input in address field."""
        response = self.client.post('/meshc/api/link-token/',
            data=json.dumps({'address': "'; DROP TABLE users;--", 'symbol': 'USDC'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    @patch('meshsbox.views.create_sandbox_cex_token')
    @patch('meshsbox.views.load_config')
    def test_cex_success(self, mock_config, mock_create):
        """API generates CEX token successfully."""
        mock_config.return_value = {'client_id': 'x', 'client_secret': 'x', 'api_url': 'x'}
        mock_create.return_value = MagicMock(token='tok', expires_at='2025-01-01')

        # Valid Stellar address (56 chars: G + 55 base32)
        valid_stellar = 'GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX'
        response = self.client.post('/meshc/api/link-token/',
            data=json.dumps({'address': valid_stellar}), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['link_token'], 'tok')

    @patch('meshsbox.views.create_sandbox_wallet_token')
    @patch('meshsbox.views.load_config')
    def test_wallet_mode(self, mock_config, mock_create):
        """API generates wallet token when wallet=true."""
        mock_config.return_value = {'client_id': 'x', 'client_secret': 'x', 'api_url': 'x'}
        mock_create.return_value = MagicMock(token='wtok', expires_at='2025-01-01')

        # Valid Ethereum address (42 chars: 0x + 40 hex)
        valid_eth = '0xF4c2AFcbE0c52FA4482AE618CEF5aBe4e5E5388c'
        response = self.client.post('/meshc/api/link-token/',
            data=json.dumps({'address': valid_eth, 'symbol': 'SEPOLIAETH', 'wallet': True}), content_type='application/json')

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


class WithdrawViewTests(SimpleTestCase):
    """Tests for the withdraw view (wallet → exchange)."""

    def setUp(self):
        self.client = Client()

    def test_renders(self):
        """Withdraw page loads successfully."""
        response = self.client.get('/meshc/withdraw/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Withdraw to Exchange')

    def test_contains_form_elements(self):
        """Withdraw page contains required form elements."""
        response = self.client.get('/meshc/withdraw/')
        self.assertContains(response, 'user_id')
        self.assertContains(response, 'symbol')
        self.assertContains(response, 'easy_relogin')


class ApiWithdrawTokenTests(TestCase):
    """Tests for the withdraw token API endpoint."""

    def setUp(self):
        self.client = Client()

    def test_requires_post(self):
        """API rejects GET requests."""
        response = self.client.get('/meshc/api/withdraw-token/')
        self.assertEqual(response.status_code, 405)

    def test_requires_json(self):
        """API rejects non-JSON body."""
        response = self.client.post('/meshc/api/withdraw-token/', data='bad', content_type='text/plain')
        self.assertEqual(response.status_code, 400)

    def test_requires_user_id(self):
        """API requires user_id field."""
        response = self.client.post('/meshc/api/withdraw-token/',
            data=json.dumps({'exchange': 'coinbase', 'symbol': 'USDC'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('user_id', response.json()['error'])

    def test_requires_exchange(self):
        """API requires exchange field."""
        response = self.client.post('/meshc/api/withdraw-token/',
            data=json.dumps({'user_id': 'test', 'symbol': 'USDC'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('exchange', response.json()['error'])

    def test_requires_symbol(self):
        """API requires symbol field."""
        response = self.client.post('/meshc/api/withdraw-token/',
            data=json.dumps({'user_id': 'test', 'exchange': 'coinbase'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('symbol', response.json()['error'])

    def test_rejects_unsupported_symbol(self):
        """API rejects unsupported symbol."""
        response = self.client.post('/meshc/api/withdraw-token/',
            data=json.dumps({'user_id': 'test', 'exchange': 'coinbase', 'symbol': 'DOGE'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Unsupported symbol', response.json()['error'])

    def test_needs_auth_when_no_stored_token(self):
        """Returns needs_auth=true when no stored token exists."""
        response = self.client.post('/meshc/api/withdraw-token/',
            data=json.dumps({
                'user_id': 'GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX',
                'exchange': 'coinbase',
                'symbol': 'USDC'
            }),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('needs_auth'))
        self.assertEqual(data.get('exchange'), 'coinbase')
        self.assertEqual(data.get('integration_type'), 'Coinbase')

    @patch('meshsbox.views.create_link_token')
    @patch('meshsbox.views.load_config')
    def test_auth_mode_returns_link_token(self, mock_config, mock_create):
        """Auth mode returns link token for exchange connection."""
        mock_config.return_value = {'client_id': 'x', 'client_secret': 'x', 'api_url': 'https://sandbox.test'}
        mock_create.return_value = MagicMock(token='auth-link-token', expires_at='2025-01-01')

        response = self.client.post('/meshc/api/withdraw-token/',
            data=json.dumps({
                'user_id': 'GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX',
                'exchange': 'coinbase',
                'symbol': 'USDC',
                'mode': 'auth'
            }),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['link_token'], 'auth-link-token')
        self.assertEqual(data['mode'], 'auth')

    def test_transfer_mode_with_fresh_auth_token(self):
        """Transfer mode with fresh auth_token returns has_token for deposit-token call."""
        response = self.client.post('/meshc/api/withdraw-token/',
            data=json.dumps({
                'user_id': 'GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX',
                'exchange': 'coinbase',
                'symbol': 'USDC',
                'auth_token': 'fresh-auth-token'
            }),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # api_withdraw_token now returns has_token + auth_token for frontend to use with api_deposit_token
        self.assertTrue(data['has_token'])
        self.assertEqual(data['auth_token'], 'fresh-auth-token')
        self.assertEqual(data['exchange'], 'coinbase')

    def test_transfer_mode_with_stored_token(self):
        """Transfer mode returns stored token from database."""
        # Create stored token
        from meshsbox.models import IntegrationToken
        IntegrationToken.objects.create(
            token_id='stored-auth-token',
            integration_type='Coinbase',
            user_id='GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX',
            status='active',
        )

        response = self.client.post('/meshc/api/withdraw-token/',
            data=json.dumps({
                'user_id': 'GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX',
                'exchange': 'coinbase',
                'symbol': 'USDC',
            }),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # api_withdraw_token returns has_token + stored auth_token
        self.assertTrue(data['has_token'])
        self.assertEqual(data['auth_token'], 'stored-auth-token')


class ApiDepositTokenTests(TestCase):
    """Tests for the deposit token API endpoint (fetches deposit address and creates transfer token)."""

    def setUp(self):
        self.client = Client()

    def test_requires_post(self):
        """API rejects GET requests."""
        response = self.client.get('/meshc/api/deposit-token/')
        self.assertEqual(response.status_code, 405)

    def test_requires_json(self):
        """API rejects non-JSON body."""
        response = self.client.post('/meshc/api/deposit-token/', data='bad', content_type='text/plain')
        self.assertEqual(response.status_code, 400)

    def test_requires_auth_token(self):
        """API requires auth_token field."""
        response = self.client.post('/meshc/api/deposit-token/',
            data=json.dumps({
                'user_id': 'test',
                'exchange': 'coinbase',
                'symbol': 'USDC'
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('auth_token', response.json()['error'])

    def test_rejects_unsupported_symbol(self):
        """API rejects unsupported symbol."""
        response = self.client.post('/meshc/api/deposit-token/',
            data=json.dumps({
                'user_id': 'test',
                'exchange': 'coinbase',
                'symbol': 'DOGE',
                'auth_token': 'test-token'
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Unsupported symbol', response.json()['error'])

    @patch('meshsbox.views.create_link_token')
    @patch('meshsbox.views.get_exchange_deposit_address')
    @patch('meshsbox.views.load_config')
    def test_fetches_deposit_address_and_returns_link_token(self, mock_config, mock_get_addr, mock_create):
        """API fetches deposit address and creates link token."""
        mock_config.return_value = {'client_id': 'x', 'client_secret': 'x', 'api_url': 'https://sandbox.test'}
        mock_get_addr.return_value = MagicMock(address='0x1234abcd5678', chain='ETH')
        mock_create.return_value = MagicMock(token='transfer-link-token', expires_at='2025-01-01')

        response = self.client.post('/meshc/api/deposit-token/',
            data=json.dumps({
                'user_id': 'GBXYIBA4JX4BMI4RGDI7XEKKTFIGM3AV5T7L7R2IN6L6QOWYDVKQA5NX',
                'exchange': 'coinbase',
                'symbol': 'USDC',
                'auth_token': 'valid-auth-token'
            }),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['link_token'], 'transfer-link-token')
        self.assertEqual(data['deposit_address'], '0x1234abcd5678')
        self.assertEqual(data['chain'], 'ETH')

        # Verify correct API calls
        mock_get_addr.assert_called_once()
        call_kwargs = mock_get_addr.call_args[1]
        self.assertEqual(call_kwargs['auth_token'], 'valid-auth-token')
        self.assertEqual(call_kwargs['symbol'], 'USDC')

    @patch('meshsbox.views.get_exchange_deposit_address')
    @patch('meshsbox.views.load_config')
    def test_invalid_auth_token_returns_error(self, mock_config, mock_get_addr):
        """API returns error when auth token is invalid/expired."""
        mock_config.return_value = {'client_id': 'x', 'client_secret': 'x', 'api_url': 'https://sandbox.test'}
        mock_get_addr.side_effect = Exception('API error: Invalid authToken provided')

        response = self.client.post('/meshc/api/deposit-token/',
            data=json.dumps({
                'user_id': 'test',
                'exchange': 'coinbase',
                'symbol': 'USDC',
                'auth_token': 'expired-token'
            }),
            content_type='application/json')

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('Invalid authToken', data['error'])


class ApiSaveTokenTests(TestCase):
    """Tests for the save token API endpoint (Easy Relogin)."""

    def setUp(self):
        self.client = Client()

    def test_requires_post(self):
        """API rejects GET requests."""
        response = self.client.get('/meshc/api/save-token/')
        self.assertEqual(response.status_code, 405)

    def test_requires_all_fields(self):
        """API requires token_id, integration_type, and user_id."""
        response = self.client.post('/meshc/api/save-token/',
            data=json.dumps({'token_id': 'tok'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_creates_new_token(self):
        """Creates new IntegrationToken record."""
        response = self.client.post('/meshc/api/save-token/',
            data=json.dumps({
                'token_id': 'new-token-123',
                'integration_type': 'Coinbase',
                'user_id': 'GBXYUSER...'
            }),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'saved')
        self.assertEqual(data['action'], 'created')

        from meshsbox.models import IntegrationToken
        token = IntegrationToken.objects.get(token_id='new-token-123')
        self.assertEqual(token.integration_type, 'Coinbase')
        self.assertEqual(token.user_id, 'GBXYUSER...')
        self.assertEqual(token.status, 'active')

    def test_updates_existing_token(self):
        """Updates existing IntegrationToken record."""
        from meshsbox.models import IntegrationToken
        IntegrationToken.objects.create(
            token_id='existing-token',
            integration_type='Coinbase',
            user_id='old-user',
            status='active',
        )

        response = self.client.post('/meshc/api/save-token/',
            data=json.dumps({
                'token_id': 'existing-token',
                'integration_type': 'Coinbase',
                'user_id': 'new-user'
            }),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['action'], 'updated')

        token = IntegrationToken.objects.get(token_id='existing-token')
        self.assertEqual(token.user_id, 'new-user')
