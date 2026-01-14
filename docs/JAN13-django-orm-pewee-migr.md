# Peewee → Django ORM Migration

**Date**: 2026-01-13
**Status**: Implementation

## Goal
Replace Peewee with Django ORM. Same API, new backend.

## Changes (4 files)

### 1. Add Model → `meshc_django/meshsbox/models.py`
```python
class IntegrationToken(models.Model):
    token_id = models.CharField(max_length=255, db_index=True)
    integration_type = models.CharField(max_length=64, db_index=True)
    user_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    wallet_address = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    scope = models.CharField(max_length=16, default='read')
    status = models.CharField(max_length=16, default='active', db_index=True)
    lang = models.CharField(max_length=8, default='en')
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integration_tokens'
        constraints = [models.UniqueConstraint(fields=['token_id', 'integration_type'], name='unique_token_type')]
```

### 2. Add Admin → `meshc_django/meshsbox/admin.py`
```python
@admin.register(IntegrationToken)
class IntegrationTokenAdmin(admin.ModelAdmin):
    list_display = ['token_short', 'integration_type', 'user_id', 'wallet_short', 'status', 'created_at']
    list_filter = ['status', 'integration_type']
    search_fields = ['token_id', 'user_id', 'wallet_address']
    actions = ['revoke_tokens']
```

### 3. Replace Backend → `src/meshc/storage.py`
Replace Peewee with Django ORM. Key pattern:
```python
def _django_setup():
    """Bootstrap Django for CLI use."""
    import django
    from django.conf import settings
    if not settings.configured:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'meshc_django'))
        settings.configure(
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3',
                                   'NAME': str(Path(__file__).parent.parent.parent / 'meshc_django/db.sqlite3')}},
            INSTALLED_APPS=['meshsbox'],
        )
        django.setup()
```

Same functions, new implementation:
- `init_db()` → calls `_django_setup()`
- `store_token()` → `IntegrationToken.objects.update_or_create()`
- `get_token()` → `IntegrationToken.objects.filter().first()`
- `list_tokens()` → `IntegrationToken.objects.filter()`
- `revoke_token()` → `IntegrationToken.objects.filter().update(status='revoked')`
- `delete_token()` → `IntegrationToken.objects.filter().delete()`

### 4. Run Migration
```bash
cd meshc_django && python manage.py makemigrations && python manage.py migrate
```

## Verification
1. `meshc token-store test123 Coinbase` - Store via CLI
2. Django admin shows the token
3. `meshc token-list` - List via CLI
