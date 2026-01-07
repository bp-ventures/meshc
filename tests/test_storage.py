"""Tests for meshc.storage module."""
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from meshc.storage import (
    IntegrationToken,
    delete_token,
    get_token,
    init_db,
    list_tokens,
    revoke_token,
    store_token,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_tokens.db"
    init_db(db_path)
    yield db_path
    # Cleanup happens automatically with tmp_path


class TestDatabaseInit:
    def test_init_creates_database(self, tmp_path):
        """Test that init_db creates database file."""
        db_path = tmp_path / "tokens.db"
        init_db(db_path)
        assert db_path.exists()

    def test_init_creates_parent_directory(self, tmp_path):
        """Test that init_db creates parent directories."""
        db_path = tmp_path / "subdir" / "nested" / "tokens.db"
        init_db(db_path)
        assert db_path.exists()
        assert db_path.parent.exists()

    def test_init_is_idempotent(self, tmp_path):
        """Test that init_db can be called multiple times safely."""
        db_path = tmp_path / "tokens.db"
        init_db(db_path)
        init_db(db_path)  # Should not raise
        assert db_path.exists()


class TestStoreToken:
    def test_store_new_token(self, temp_db):
        """Test storing a new token."""
        token = store_token(
            token_id="tok_abc123",
            integration_type="Coinbase",
            user_id="user123",
            scope="read",
        )

        assert token.token_id == "tok_abc123"
        assert token.integration_type == "Coinbase"
        assert token.user_id == "user123"
        assert token.scope == "read"
        assert token.status == "active"
        assert token.lang == "en"  # Default language
        assert token.wallet_address is None

    def test_store_token_with_wallet(self, temp_db):
        """Test storing a token with wallet address."""
        token = store_token(
            token_id="tok_wallet123",
            integration_type="MetaMask",
            wallet_address="0x1234567890abcdef",
            scope="write",
        )

        assert token.wallet_address == "0x1234567890abcdef"
        assert token.user_id is None
        assert token.scope == "write"

    def test_update_existing_token(self, temp_db):
        """Test that storing same token_id updates existing record."""
        # Store initial token
        token1 = store_token(
            token_id="tok_update",
            integration_type="Binance",
            user_id="user1",
            scope="read",
        )

        # Store again with different values
        token2 = store_token(
            token_id="tok_update",
            integration_type="Binance",
            user_id="user2",  # Changed
            scope="write",    # Changed
        )

        # Should be same database record (same ID)
        assert token1.id == token2.id
        assert token2.user_id == "user2"
        assert token2.scope == "write"

        # Should only have one record
        all_tokens = list_tokens()
        assert len(all_tokens) == 1

    def test_store_with_metadata(self, temp_db):
        """Test storing token with metadata."""
        metadata = {"exchange_id": "123", "permissions": ["read", "trade"]}
        token = store_token(
            token_id="tok_meta",
            integration_type="Kraken",
            metadata=metadata,
        )

        assert token.metadata == metadata

    def test_store_with_expiration(self, temp_db):
        """Test storing token with expiration date."""
        expires_at = datetime.utcnow() + timedelta(days=30)
        token = store_token(
            token_id="tok_expire",
            integration_type="Coinbase",
            expires_at=expires_at,
        )

        assert token.expires_at is not None
        assert isinstance(token.expires_at, datetime)

    def test_store_with_lang(self, temp_db):
        """Test storing token with language preference."""
        token = store_token(
            token_id="tok_lang",
            integration_type="Coinbase",
            user_id="user123",
            lang="fr",
        )

        assert token.lang == "fr"

    def test_store_with_different_languages(self, temp_db):
        """Test storing tokens with different language codes."""
        langs = ["en", "fr", "es", "de", "ja"]

        for i, lang in enumerate(langs):
            token = store_token(
                token_id=f"tok_lang_{i}",
                integration_type="Coinbase",
                user_id=f"user_{i}",
                lang=lang,
            )
            assert token.lang == lang


class TestGetToken:
    def test_get_existing_token(self, temp_db):
        """Test retrieving an existing token."""
        store_token(
            token_id="tok_get",
            integration_type="Coinbase",
            user_id="user123",
        )

        token = get_token("tok_get")
        assert token is not None
        assert token.token_id == "tok_get"
        assert token.user_id == "user123"

    def test_get_nonexistent_token(self, temp_db):
        """Test retrieving a non-existent token returns None."""
        token = get_token("tok_nonexistent")
        assert token is None

    def test_get_with_integration_type_filter(self, temp_db):
        """Test getting token with integration type filter."""
        store_token("tok_1", "Coinbase", user_id="user1")
        store_token("tok_1", "Binance", user_id="user2")  # Same token_id, different type

        token = get_token("tok_1", integration_type="Binance")
        assert token.integration_type == "Binance"
        assert token.user_id == "user2"


class TestListTokens:
    def test_list_all_tokens(self, temp_db):
        """Test listing all tokens."""
        store_token("tok_1", "Coinbase", user_id="user1")
        store_token("tok_2", "Binance", user_id="user2")
        store_token("tok_3", "Kraken", user_id="user3")

        tokens = list_tokens()
        assert len(tokens) == 3

    def test_list_empty(self, temp_db):
        """Test listing when no tokens exist."""
        tokens = list_tokens()
        assert tokens == []

    def test_list_by_user_id(self, temp_db):
        """Test filtering tokens by user_id."""
        store_token("tok_1", "Coinbase", user_id="alice")
        store_token("tok_2", "Binance", user_id="bob")
        store_token("tok_3", "Kraken", user_id="alice")

        tokens = list_tokens(user_id="alice")
        assert len(tokens) == 2
        assert all(t.user_id == "alice" for t in tokens)

    def test_list_by_wallet_address(self, temp_db):
        """Test filtering tokens by wallet address."""
        store_token("tok_1", "MetaMask", wallet_address="0xaaa")
        store_token("tok_2", "Rainbow", wallet_address="0xbbb")
        store_token("tok_3", "MetaMask", wallet_address="0xaaa")

        tokens = list_tokens(wallet_address="0xaaa")
        assert len(tokens) == 2
        assert all(t.wallet_address == "0xaaa" for t in tokens)

    def test_list_by_integration_type(self, temp_db):
        """Test filtering tokens by integration type."""
        store_token("tok_1", "Coinbase", user_id="user1")
        store_token("tok_2", "Coinbase", user_id="user2")
        store_token("tok_3", "Binance", user_id="user3")

        tokens = list_tokens(integration_type="Coinbase")
        assert len(tokens) == 2
        assert all(t.integration_type == "Coinbase" for t in tokens)

    def test_list_active_only(self, temp_db):
        """Test filtering for active tokens only."""
        store_token("tok_1", "Coinbase", user_id="user1")
        store_token("tok_2", "Binance", user_id="user2")
        revoke_token("tok_2")  # Mark as revoked

        tokens = list_tokens(active_only=True)
        assert len(tokens) == 1
        assert tokens[0].token_id == "tok_1"

    def test_list_ordered_by_created_desc(self, temp_db):
        """Test that tokens are ordered by created_at descending."""
        import time

        store_token("tok_1", "Coinbase", user_id="user1")
        time.sleep(0.01)  # Ensure different timestamps
        store_token("tok_2", "Binance", user_id="user2")
        time.sleep(0.01)
        store_token("tok_3", "Kraken", user_id="user3")

        tokens = list_tokens()
        # Most recent first
        assert tokens[0].token_id == "tok_3"
        assert tokens[1].token_id == "tok_2"
        assert tokens[2].token_id == "tok_1"


class TestRevokeToken:
    def test_revoke_existing_token(self, temp_db):
        """Test revoking a token."""
        store_token("tok_revoke", "Coinbase", user_id="user1")

        success = revoke_token("tok_revoke")
        assert success is True

        token = get_token("tok_revoke")
        assert token.status == "revoked"

    def test_revoke_nonexistent_token(self, temp_db):
        """Test revoking a non-existent token returns False."""
        success = revoke_token("tok_nonexistent")
        assert success is False

    def test_revoke_with_integration_type_filter(self, temp_db):
        """Test revoking with integration type filter."""
        store_token("tok_1", "Coinbase", user_id="user1")
        store_token("tok_1", "Binance", user_id="user2")

        success = revoke_token("tok_1", integration_type="Binance")
        assert success is True

        # Only Binance token should be revoked
        coinbase_token = get_token("tok_1", integration_type="Coinbase")
        binance_token = get_token("tok_1", integration_type="Binance")

        assert coinbase_token.status == "active"
        assert binance_token.status == "revoked"


class TestDeleteToken:
    def test_delete_existing_token(self, temp_db):
        """Test deleting a token permanently."""
        store_token("tok_delete", "Coinbase", user_id="user1")

        success = delete_token("tok_delete")
        assert success is True

        token = get_token("tok_delete")
        assert token is None

    def test_delete_nonexistent_token(self, temp_db):
        """Test deleting a non-existent token returns False."""
        success = delete_token("tok_nonexistent")
        assert success is False

    def test_delete_with_integration_type_filter(self, temp_db):
        """Test deleting with integration type filter."""
        store_token("tok_1", "Coinbase", user_id="user1")
        store_token("tok_1", "Binance", user_id="user2")

        success = delete_token("tok_1", integration_type="Binance")
        assert success is True

        # Only Binance token should be deleted
        coinbase_token = get_token("tok_1", integration_type="Coinbase")
        binance_token = get_token("tok_1", integration_type="Binance")

        assert coinbase_token is not None
        assert binance_token is None


class TestIntegrationTokenModel:
    def test_is_active_property(self, temp_db):
        """Test is_active property."""
        token = store_token("tok_active", "Coinbase", user_id="user1")
        assert token.is_active is True

        revoke_token("tok_active")
        token = get_token("tok_active")
        assert token.is_active is False

    def test_is_expired_property_not_expired(self, temp_db):
        """Test is_expired returns False for future expiration."""
        expires_at = datetime.utcnow() + timedelta(days=30)
        token = store_token(
            "tok_future",
            "Coinbase",
            expires_at=expires_at,
        )
        assert token.is_expired is False

    def test_is_expired_property_expired(self, temp_db):
        """Test is_expired returns True for past expiration."""
        expires_at = datetime.utcnow() - timedelta(days=1)
        token = store_token(
            "tok_past",
            "Coinbase",
            expires_at=expires_at,
        )
        assert token.is_expired is True

    def test_is_expired_property_no_expiration(self, temp_db):
        """Test is_expired returns False when no expiration set."""
        token = store_token("tok_none", "Coinbase")
        assert token.is_expired is False

    def test_to_dict_serialization(self, temp_db):
        """Test to_dict converts token to dictionary."""
        metadata = {"key": "value"}
        expires_at = datetime.utcnow() + timedelta(days=30)

        token = store_token(
            token_id="tok_dict",
            integration_type="Coinbase",
            user_id="user123",
            wallet_address="0xabc",
            scope="write",
            lang="fr",
            expires_at=expires_at,
            metadata=metadata,
        )

        token_dict = token.to_dict()

        assert token_dict["token_id"] == "tok_dict"
        assert token_dict["integration_type"] == "Coinbase"
        assert token_dict["user_id"] == "user123"
        assert token_dict["wallet_address"] == "0xabc"
        assert token_dict["scope"] == "write"
        assert token_dict["status"] == "active"
        assert token_dict["lang"] == "fr"
        assert token_dict["metadata"] == metadata
        assert isinstance(token_dict["created_at"], str)
        assert token_dict["created_at"].endswith("Z")
        assert isinstance(token_dict["expires_at"], str)

    def test_save_updates_timestamp(self, temp_db):
        """Test that save() updates the updated_at timestamp."""
        import time

        token = store_token("tok_save", "Coinbase", user_id="user1")
        original_updated_at = token.updated_at

        time.sleep(0.01)  # Ensure timestamp difference

        token.scope = "write"
        token.save()

        assert token.updated_at > original_updated_at
