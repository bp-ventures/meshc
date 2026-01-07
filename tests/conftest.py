"""Pytest fixtures for meshc tests."""
import pytest


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "api_url": "https://sandbox-integration-api.meshconnect.com",
        "stellar_network_id": "06855704-43d2-4ad2-a73c-372f0c3534e1",
    }


@pytest.fixture
def mock_link_token_response():
    """Mock API response for link token creation."""
    return {
        "content": {
            "linkToken": "mock-link-token-abc123",
            "expiresAt": "2025-01-01T00:00:00Z",
        }
    }


@pytest.fixture
def mock_networks_response():
    """Mock API response for networks."""
    return {
        "content": {
            "networks": [
                {
                    "id": "06855704-43d2-4ad2-a73c-372f0c3534e1",
                    "name": "Stellar",
                    "supportedTokens": ["USDC", "XLM", "EURC"],
                    "supportedBrokerTypes": ["coinbase", "robinhood"],
                },
                {
                    "id": "e3c7fdd8-b1fc-4e51-85ae-bb276e075611",
                    "name": "Ethereum",
                    "supportedTokens": ["ETH", "USDC", "USDT"],
                    "supportedBrokerTypes": ["coinbase"],
                },
            ]
        }
    }
