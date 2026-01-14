"""Token storage backend using Django ORM.

Lightweight storage for Mesh Managed Tokens (MMT).
Thread-safe, Django-powered, shared with web admin.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("meshc")

# Django app path - relative to this file
_DJANGO_PROJECT_PATH = Path(__file__).parent.parent.parent / 'meshc_django'
_DJANGO_DB_PATH = _DJANGO_PROJECT_PATH / 'db.sqlite3'

_django_configured = False


def _django_setup() -> None:
    """Bootstrap Django for CLI use (standalone mode)."""
    global _django_configured
    if _django_configured:
        return

    import django
    from django.conf import settings

    if settings.configured:
        _django_configured = True
        return

    # Add meshc_django to path so meshsbox is importable
    if str(_DJANGO_PROJECT_PATH) not in sys.path:
        sys.path.insert(0, str(_DJANGO_PROJECT_PATH))

    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': str(_DJANGO_DB_PATH),
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'meshsbox',
        ],
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
        USE_TZ=True,
    )
    django.setup()
    _django_configured = True
    logger.debug("django storage initialized at %s", _DJANGO_DB_PATH)


def _get_model():
    """Lazy import of IntegrationToken model."""
    _django_setup()
    from meshsbox.models import IntegrationToken
    return IntegrationToken


# Lazy reference to IntegrationToken model for external imports
# Usage: from meshc.storage import IntegrationToken; model = IntegrationToken()
class _LazyModel:
    """Lazy proxy to Django IntegrationToken model."""
    _model = None

    def __getattr__(self, name):
        if _LazyModel._model is None:
            _LazyModel._model = _get_model()
        return getattr(_LazyModel._model, name)

    def __call__(self, *args, **kwargs):
        if _LazyModel._model is None:
            _LazyModel._model = _get_model()
        return _LazyModel._model(*args, **kwargs)


IntegrationToken = _LazyModel()


# -----------------------------------------------------------------------------
# Public API (same signatures as original Peewee version)
# -----------------------------------------------------------------------------


def init_db(db_path: str | Path | None = None) -> None:
    """Initialize database connection and create tables.

    Args:
        db_path: Ignored (uses Django's configured database)

    Safe to call multiple times (idempotent).
    """
    _django_setup()

    # Ensure tables exist via migrate --run-syncdb
    from django.core.management import call_command
    call_command('migrate', '--run-syncdb', verbosity=0)
    logger.debug("database tables synced")


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
):
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
    IntegrationToken = _get_model()

    # Parse expires_at if string
    if isinstance(expires_at, str):
        try:
            from django.utils.dateparse import parse_datetime
            expires_at = parse_datetime(expires_at.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            logger.warning("invalid expires_at format, ignoring: %s", expires_at)
            expires_at = None

    token, created = IntegrationToken.objects.update_or_create(
        token_id=token_id,
        integration_type=integration_type,
        defaults={
            'user_id': user_id,
            'wallet_address': wallet_address,
            'scope': scope or 'read',
            'lang': lang or 'en',  # Ensure non-null
            'expires_at': expires_at,
            'metadata': metadata or {},
        }
    )

    if created:
        logger.info("stored new token %s (%s)", token_id[:12], integration_type)
    else:
        logger.debug("updated token %s (%s)", token_id[:12], integration_type)

    return token


def get_token(
    token_id: str,
    integration_type: str | None = None,
):
    """Get a token by ID.

    Args:
        token_id: Mesh token ID to retrieve
        integration_type: Optional integration type filter

    Returns:
        IntegrationToken if found, None otherwise
    """
    IntegrationToken = _get_model()

    qs = IntegrationToken.objects.filter(token_id=token_id)
    if integration_type:
        qs = qs.filter(integration_type=integration_type)

    return qs.first()


def list_tokens(
    user_id: str | None = None,
    wallet_address: str | None = None,
    integration_type: str | None = None,
    active_only: bool = False,
) -> list:
    """List tokens with optional filters.

    Args:
        user_id: Filter by user ID
        wallet_address: Filter by wallet address
        integration_type: Filter by integration type
        active_only: Only return active tokens

    Returns:
        List of IntegrationToken instances, ordered by created_at desc
    """
    IntegrationToken = _get_model()

    qs = IntegrationToken.objects.all()

    if user_id:
        qs = qs.filter(user_id=user_id)
    if wallet_address:
        qs = qs.filter(wallet_address=wallet_address)
    if integration_type:
        qs = qs.filter(integration_type=integration_type)
    if active_only:
        qs = qs.filter(status='active')

    return list(qs.order_by('-created_at'))


def revoke_token(
    token_id: str,
    integration_type: str | None = None,
) -> bool:
    """Mark a token as revoked.

    Soft delete - token remains in database for audit trail.

    Args:
        token_id: Token ID to revoke
        integration_type: Optional integration type filter

    Returns:
        True if token was found and revoked, False otherwise
    """
    IntegrationToken = _get_model()

    qs = IntegrationToken.objects.filter(token_id=token_id)
    if integration_type:
        qs = qs.filter(integration_type=integration_type)

    count = qs.update(status='revoked')

    if count > 0:
        logger.info("revoked token %s", token_id[:12])
        return True
    return False


def delete_token(
    token_id: str,
    integration_type: str | None = None,
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
    IntegrationToken = _get_model()

    qs = IntegrationToken.objects.filter(token_id=token_id)
    if integration_type:
        qs = qs.filter(integration_type=integration_type)

    count, _ = qs.delete()

    if count > 0:
        logger.info("deleted token %s", token_id[:12])
        return True
    return False
