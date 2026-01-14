"""Admin registration for Mesh models."""
from django.contrib import admin
from .models import MeshWebhook, IntegrationToken


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


@admin.register(IntegrationToken)
class IntegrationTokenAdmin(admin.ModelAdmin):
    """Admin view for integration tokens."""
    list_display = ['token_short', 'integration_type', 'user_or_wallet', 'scope', 'status', 'lang', 'created_at']
    list_filter = ['status', 'integration_type', 'scope']
    search_fields = ['token_id', 'user_id', 'wallet_address']
    readonly_fields = ['token_id', 'integration_type', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def token_short(self, obj):
        return obj.token_id[:20] + '...' if len(obj.token_id) > 20 else obj.token_id
    token_short.short_description = 'Token ID'

    def user_or_wallet(self, obj):
        if obj.user_id:
            return f"User: {obj.user_id}"
        if obj.wallet_address:
            addr = obj.wallet_address
            return f"Wallet: {addr[:8]}...{addr[-4:]}" if len(addr) > 16 else f"Wallet: {addr}"
        return '-'
    user_or_wallet.short_description = 'Owner'

    actions = ['revoke_tokens']

    @admin.action(description='Revoke selected tokens')
    def revoke_tokens(self, request, queryset):
        count = queryset.update(status='revoked')
        self.message_user(request, f'{count} token(s) revoked.')
