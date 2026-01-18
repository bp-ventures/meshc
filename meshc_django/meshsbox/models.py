"""Webhook storage for Mesh Connect transfer events.

One record per unique transaction_id. Multiple webhooks append to history.
"""
from django.db import models


class MeshWebhook(models.Model):
    """Store Mesh webhook events by transaction.

    Key fields extracted for querying; full payloads in history JSONField.
    """
    # Primary identifier from Mesh
    transaction_id = models.CharField(max_length=64, unique=True, db_index=True)

    # Extracted fields for querying/display
    status = models.CharField(max_length=32, db_index=True)  # Pending, Succeeded, Failed
    destination_address = models.CharField(max_length=128, db_index=True)
    token = models.CharField(max_length=16)  # USDC, ETH, etc.
    chain = models.CharField(max_length=32)  # Stellar, Ethereum
    source_provider = models.CharField(max_length=32)  # Coinbase, Binance
    amount = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    tx_hash = models.CharField(max_length=128, blank=True)

    # Full webhook history (append-only JSONField array)
    history = models.JSONField(default=list)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "meshsbox_webhook"
        ordering = ["-updated_at"]
        verbose_name = "Mesh Webhook"
        verbose_name_plural = "Mesh Webhooks"

    def __str__(self) -> str:
        return f"{self.transaction_id[:16]}... ({self.status})"

    def webhook_count(self) -> int:
        """Number of webhooks received for this transaction."""
        return len(self.history)


class IntegrationToken(models.Model):
    """Mesh integration token storage for reuse across sessions (MMT).

    Supports CEX integrations (user_id) and wallet integrations (wallet_address).
    Composite unique on (token_id, integration_type).
    """
    token_id = models.CharField(max_length=1024, db_index=True)
    integration_type = models.CharField(max_length=64, db_index=True)  # Coinbase, Binance, MetaMask
    user_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    wallet_address = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    scope = models.CharField(max_length=16, default='read')  # read, write
    status = models.CharField(max_length=16, default='active', db_index=True)  # active, revoked, expired
    lang = models.CharField(max_length=8, default='en')
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integration_tokens'
        ordering = ['-created_at']
        verbose_name = 'Integration Token'
        verbose_name_plural = 'Integration Tokens'
        constraints = [
            models.UniqueConstraint(fields=['token_id', 'integration_type'], name='unique_token_type')
        ]

    def __str__(self) -> str:
        return f"{self.token_id[:16]}... ({self.integration_type})"

    @property
    def is_active(self) -> bool:
        return self.status == 'active'

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            'id': self.pk,
            'token_id': self.token_id,
            'integration_type': self.integration_type,
            'user_id': self.user_id,
            'wallet_address': self.wallet_address,
            'scope': self.scope,
            'status': self.status,
            'lang': self.lang,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() + 'Z' if self.expires_at else None,
            'metadata': self.metadata,
        }
