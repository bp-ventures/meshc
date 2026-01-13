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
