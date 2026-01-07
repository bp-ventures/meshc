"""Token storage backend using Peewee ORM.

Lightweight SQLite storage for Mesh Managed Tokens (MMT).
Thread-safe, Unix-simple, Django-like API.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from peewee import (
    CharField,
    DateTimeField,
    DoesNotExist,
    Model,
    SqliteDatabase,
)
from playhouse.sqlite_ext import JSONField

logger = logging.getLogger("meshc")

# Database instance with WAL mode for concurrency
# Initialized lazily via init_db()
db = SqliteDatabase(None, pragmas={'journal_mode': 'wal'})


class IntegrationToken(Model):
    """ORM model for integration tokens.

    Stores Mesh tokenIds with metadata for reuse across sessions.
    Supports both CEX integrations (user_id) and wallet integrations (wallet_address).
    """

    token_id = CharField(index=True)
    integration_type = CharField(index=True)  # "Coinbase", "Binance", "MetaMask", etc.
    user_id = CharField(null=True, index=True)  # App user identifier
    wallet_address = CharField(null=True, index=True)  # Wallet public key
    scope = CharField(default='read')  # "read" or "write"
    status = CharField(default='active', index=True)  # "active", "revoked", "expired"
    lang = CharField(null=True, default='en', index=True)  # User language: "en", "fr", "es", etc.
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    expires_at = DateTimeField(null=True)
    metadata = JSONField(default=dict)  # Additional data as JSON

    class Meta:
        database = db
        table_name = 'integration_tokens'
        indexes = (
            # Composite unique index on token_id + integration_type
            (('token_id', 'integration_type'), True),
        )

    @property
    def is_active(self) -> bool:
        """Check if token is currently active."""
        return self.status == 'active'

    @property
    def is_expired(self) -> bool:
        """Check if token has expired (best-effort, may not be accurate)."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            'id': self.id,
            'token_id': self.token_id,
            'integration_type': self.integration_type,
            'user_id': self.user_id,
            'wallet_address': self.wallet_address,
            'scope': self.scope,
            'status': self.status,
            'lang': self.lang,
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z',
            'expires_at': self.expires_at.isoformat() + 'Z' if self.expires_at else None,
            'metadata': self.metadata,
        }

    def save(self, *args, **kwargs):
        """Override save to update updated_at timestamp."""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)


# -----------------------------------------------------------------------------
# Module Functions (Public API)
# -----------------------------------------------------------------------------


def init_db(db_path: str | Path) -> None:
    """Initialize database connection and create tables.

    Args:
        db_path: Path to SQLite database file

    Creates parent directory if it doesn't exist.
    Safe to call multiple times (idempotent).
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db.init(str(db_path))
    db.connect()
    db.create_tables([IntegrationToken], safe=True)
    logger.debug("token storage initialized at %s", db_path)


def store_token(
    token_id: str,
    integration_type: str,
    *,
    user_id: str | None = None,
    wallet_address: str | None = None,
    scope: str = 'read',
    lang: str = 'en',
    expires_at: datetime | str | None = None,
    metadata: dict[str, Any] | None = None,
) -> IntegrationToken:
    """Store or update an integration token.

    Uses upsert pattern: inserts if new, updates if exists.

    Args:
        token_id: Mesh token ID
        integration_type: Integration name (e.g., "Coinbase", "Binance")
        user_id: Application user identifier (optional)
        wallet_address: Wallet public key (optional)
        scope: Token scope ("read" or "write")
        lang: User language code (e.g., "en", "fr", "es")
        expires_at: Expiration timestamp (datetime or ISO string)
        metadata: Additional metadata as dict

    Returns:
        Stored IntegrationToken instance
    """
    # Convert string timestamp to datetime if needed
    if isinstance(expires_at, str):
        try:
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except ValueError:
            logger.warning("invalid expires_at format, ignoring: %s", expires_at)
            expires_at = None

    defaults = {
        'user_id': user_id,
        'wallet_address': wallet_address,
        'scope': scope,
        'lang': lang,
        'expires_at': expires_at,
        'metadata': metadata or {},
    }

    token, created = IntegrationToken.get_or_create(
        token_id=token_id,
        integration_type=integration_type,
        defaults=defaults
    )

    if not created:
        # Update existing token
        for key, value in defaults.items():
            setattr(token, key, value)
        token.save()
        logger.debug("updated token %s (%s)", token_id[:12], integration_type)
    else:
        logger.info("stored new token %s (%s)", token_id[:12], integration_type)

    return token


def get_token(
    token_id: str,
    integration_type: str | None = None
) -> IntegrationToken | None:
    """Get a token by ID.

    Args:
        token_id: Mesh token ID to retrieve
        integration_type: Optional integration type filter

    Returns:
        IntegrationToken if found, None otherwise
    """
    try:
        query = IntegrationToken.select().where(
            IntegrationToken.token_id == token_id
        )
        if integration_type:
            query = query.where(IntegrationToken.integration_type == integration_type)
        return query.get()
    except DoesNotExist:
        return None


def list_tokens(
    user_id: str | None = None,
    wallet_address: str | None = None,
    integration_type: str | None = None,
    active_only: bool = False,
) -> list[IntegrationToken]:
    """List tokens with optional filters.

    Args:
        user_id: Filter by user ID
        wallet_address: Filter by wallet address
        integration_type: Filter by integration type
        active_only: Only return active tokens

    Returns:
        List of IntegrationToken instances, ordered by created_at desc
    """
    query = IntegrationToken.select()

    if user_id:
        query = query.where(IntegrationToken.user_id == user_id)
    if wallet_address:
        query = query.where(IntegrationToken.wallet_address == wallet_address)
    if integration_type:
        query = query.where(IntegrationToken.integration_type == integration_type)
    if active_only:
        query = query.where(IntegrationToken.status == 'active')

    return list(query.order_by(IntegrationToken.created_at.desc()))


def revoke_token(
    token_id: str,
    integration_type: str | None = None
) -> bool:
    """Mark a token as revoked.

    Soft delete - token remains in database for audit trail.

    Args:
        token_id: Token ID to revoke
        integration_type: Optional integration type filter

    Returns:
        True if token was found and revoked, False otherwise
    """
    query = IntegrationToken.update(
        status='revoked',
        updated_at=datetime.utcnow()
    ).where(IntegrationToken.token_id == token_id)

    if integration_type:
        query = query.where(IntegrationToken.integration_type == integration_type)

    rows_updated = query.execute()

    if rows_updated > 0:
        logger.info("revoked token %s", token_id[:12])
        return True
    return False


def delete_token(
    token_id: str,
    integration_type: str | None = None
) -> bool:
    """Permanently delete a token.

    Hard delete - removes token from database.
    Consider using revoke_token() instead for audit trail.

    Args:
        token_id: Token ID to delete
        integration_type: Optional integration type filter

    Returns:
        True if token was found and deleted, False otherwise
    """
    query = IntegrationToken.delete().where(
        IntegrationToken.token_id == token_id
    )

    if integration_type:
        query = query.where(IntegrationToken.integration_type == integration_type)

    rows_deleted = query.execute()

    if rows_deleted > 0:
        logger.info("deleted token %s", token_id[:12])
        return True
    return False
