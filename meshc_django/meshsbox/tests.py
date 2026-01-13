"""Tests for meshsbox Django app."""
import json
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase, Client


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
