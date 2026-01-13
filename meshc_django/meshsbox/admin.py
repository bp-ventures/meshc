"""Admin registration for Mesh webhook model."""
from django.contrib import admin
from .models import MeshWebhook


@admin.register(MeshWebhook)
class MeshWebhookAdmin(admin.ModelAdmin):
    """Admin view for webhook records."""
    list_display = ["transaction_id_short", "status", "token", "amount", "chain", "source_provider", "event_count", "updated_at"]
    list_filter = ["status", "chain", "source_provider", "token"]
    search_fields = ["transaction_id", "destination_address", "tx_hash"]
    readonly_fields = ["transaction_id", "history", "created_at", "updated_at"]
    ordering = ["-updated_at"]

    def transaction_id_short(self, obj):
        return obj.transaction_id[:16] + "..."
    transaction_id_short.short_description = "Transaction ID"

    def event_count(self, obj):
        return len(obj.history)
    event_count.short_description = "Events"
