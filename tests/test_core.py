"""Tests for meshc.core module."""
import pytest
from pytest_httpx import HTTPXMock

from meshc import (
    AccountToken,
    MeshAPIError,
    ToAddress,
    create_link_token,
    get_account_tokens_for_user,
    get_networks,
    get_stellar_network_id,
)
from meshc.storage import init_db, store_token


class TestToAddress:
    def test_to_dict_without_amount(self):
        addr = ToAddress(symbol="USDC", address="GTEST...", network_id="abc123")
        d = addr.to_dict()
        assert d == {"symbol": "USDC", "address": "GTEST...", "networkId": "abc123"}
        assert "amount" not in d

    def test_to_dict_with_amount(self):
        addr = ToAddress(symbol="XLM", address="GADDR", network_id="xyz", amount=100.5)
        d = addr.to_dict()
        assert d["amount"] == 100.5


class TestCreateLinkToken:
    def test_success(self, httpx_mock: HTTPXMock, mock_config, mock_link_token_response):
        httpx_mock.add_response(json=mock_link_token_response)

        result = create_link_token(
            client_id=mock_config["client_id"],
            client_secret=mock_config["client_secret"],
            user_id="test-user",
            to_addresses=[ToAddress("USDC", "GADDR", "net-id")],
            api_url=mock_config["api_url"],
        )

        assert result.token == "mock-link-token-abc123"
        assert result.expires_at == "2025-01-01T00:00:00Z"

    def test_api_error(self, httpx_mock: HTTPXMock, mock_config):
        httpx_mock.add_response(
            status_code=400,
            json={"message": "Invalid request"},
        )

        with pytest.raises(MeshAPIError) as exc:
            create_link_token(
                client_id=mock_config["client_id"],
                client_secret=mock_config["client_secret"],
                user_id="test-user",
                to_addresses=[],
                api_url=mock_config["api_url"],
            )

        assert exc.value.status_code == 400
        assert "Invalid request" in str(exc.value)


class TestGetNetworks:
    def test_success(self, httpx_mock: HTTPXMock, mock_config, mock_networks_response):
        httpx_mock.add_response(json=mock_networks_response)

        networks = get_networks(
            client_id=mock_config["client_id"],
            client_secret=mock_config["client_secret"],
            api_url=mock_config["api_url"],
        )

        assert len(networks) == 2
        assert networks[0].name == "Stellar"
        assert "USDC" in networks[0].tokens


class TestGetStellarNetworkId:
    def test_success(self, httpx_mock: HTTPXMock, mock_config, mock_networks_response):
        httpx_mock.add_response(json=mock_networks_response)

        network_id = get_stellar_network_id(
            client_id=mock_config["client_id"],
            client_secret=mock_config["client_secret"],
            api_url=mock_config["api_url"],
        )

        assert network_id == "06855704-43d2-4ad2-a73c-372f0c3534e1"

    def test_not_found(self, httpx_mock: HTTPXMock, mock_config):
        httpx_mock.add_response(json={"content": {"networks": []}})

        with pytest.raises(MeshAPIError) as exc:
            get_stellar_network_id(
                client_id=mock_config["client_id"],
                client_secret=mock_config["client_secret"],
                api_url=mock_config["api_url"],
            )

        assert "not found" in str(exc.value).lower()


class TestAccountToken:
    def test_to_dict(self):
        """Test AccountToken.to_dict() serialization."""
        token = AccountToken(
            token_id="tok_abc123",
            integration_type="Coinbase"
        )
        d = token.to_dict()
        assert d == {
            "tokenId": "tok_abc123",
            "type": "Coinbase"
        }


class TestCreateLinkTokenWithAccountTokens:
    def test_with_account_tokens_list(self, httpx_mock: HTTPXMock, mock_config, mock_link_token_response):
        """Test create_link_token includes accountTokens in payload."""
        account_tokens = [
            AccountToken("tok_1", "Coinbase"),
            AccountToken("tok_2", "Binance"),
        ]

        # Capture the request
        httpx_mock.add_response(json=mock_link_token_response)

        create_link_token(
            client_id=mock_config["client_id"],
            client_secret=mock_config["client_secret"],
            user_id="test-user",
            to_addresses=[ToAddress("USDC", "GADDR", "net-id")],
            account_tokens=account_tokens,
            api_url=mock_config["api_url"],
        )

        # Verify request includes accountTokens
        request = httpx_mock.get_requests()[0]
        import json
        payload = json.loads(request.content)

        assert "accountTokens" in payload
        assert len(payload["accountTokens"]) == 2
        assert payload["accountTokens"][0] == {"tokenId": "tok_1", "type": "Coinbase"}
        assert payload["accountTokens"][1] == {"tokenId": "tok_2", "type": "Binance"}

    def test_with_account_tokens_dicts(self, httpx_mock: HTTPXMock, mock_config, mock_link_token_response):
        """Test create_link_token accepts accountTokens as dicts."""
        account_tokens = [
            {"tokenId": "tok_1", "type": "Coinbase"},
            {"tokenId": "tok_2", "type": "Binance"},
        ]

        httpx_mock.add_response(json=mock_link_token_response)

        create_link_token(
            client_id=mock_config["client_id"],
            client_secret=mock_config["client_secret"],
            user_id="test-user",
            to_addresses=[ToAddress("USDC", "GADDR", "net-id")],
            account_tokens=account_tokens,
            api_url=mock_config["api_url"],
        )

        request = httpx_mock.get_requests()[0]
        import json
        payload = json.loads(request.content)

        assert "accountTokens" in payload
        assert payload["accountTokens"] == account_tokens

    def test_without_account_tokens(self, httpx_mock: HTTPXMock, mock_config, mock_link_token_response):
        """Test create_link_token without accountTokens (backwards compat)."""
        httpx_mock.add_response(json=mock_link_token_response)

        create_link_token(
            client_id=mock_config["client_id"],
            client_secret=mock_config["client_secret"],
            user_id="test-user",
            to_addresses=[ToAddress("USDC", "GADDR", "net-id")],
            api_url=mock_config["api_url"],
        )

        request = httpx_mock.get_requests()[0]
        import json
        payload = json.loads(request.content)

        assert "accountTokens" not in payload


class TestGetAccountTokensForUser:
    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database for testing."""
        db_path = tmp_path / "test_tokens.db"
        init_db(db_path)
        yield db_path

    def test_get_tokens_by_user_id(self, temp_db):
        """Test retrieving tokens for a specific user."""
        store_token("tok_1", "Coinbase", user_id="alice")
        store_token("tok_2", "Binance", user_id="alice")
        store_token("tok_3", "Kraken", user_id="bob")

        tokens = get_account_tokens_for_user(user_id="alice")

        assert len(tokens) == 2
        assert all(isinstance(t, AccountToken) for t in tokens)
        assert {t.token_id for t in tokens} == {"tok_1", "tok_2"}

    def test_get_tokens_by_wallet_address(self, temp_db):
        """Test retrieving tokens for a specific wallet."""
        store_token("tok_1", "MetaMask", wallet_address="0xaaa")
        store_token("tok_2", "Rainbow", wallet_address="0xaaa")
        store_token("tok_3", "MetaMask", wallet_address="0xbbb")

        tokens = get_account_tokens_for_user(wallet_address="0xaaa")

        assert len(tokens) == 2
        assert {t.token_id for t in tokens} == {"tok_1", "tok_2"}

    def test_get_tokens_with_integration_type_filter(self, temp_db):
        """Test filtering by integration type."""
        store_token("tok_1", "Coinbase", user_id="alice")
        store_token("tok_2", "Binance", user_id="alice")
        store_token("tok_3", "Coinbase", user_id="alice")

        tokens = get_account_tokens_for_user(
            user_id="alice",
            integration_type="Coinbase"
        )

        assert len(tokens) == 2
        assert all(t.integration_type == "Coinbase" for t in tokens)

    def test_get_tokens_only_active(self, temp_db):
        """Test that only active tokens are returned."""
        from meshc.storage import revoke_token

        store_token("tok_1", "Coinbase", user_id="alice")
        store_token("tok_2", "Binance", user_id="alice")
        revoke_token("tok_2")

        tokens = get_account_tokens_for_user(user_id="alice")

        assert len(tokens) == 1
        assert tokens[0].token_id == "tok_1"

    def test_get_tokens_no_matches(self, temp_db):
        """Test returns empty list when no tokens found."""
        tokens = get_account_tokens_for_user(user_id="nonexistent")
        assert tokens == []
