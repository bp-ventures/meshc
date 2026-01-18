# Plan: Secure MMT Token Storage with Django Encryption

## Problem Statement

MMT `token_id` values are stored as plaintext in SQLite. These tokens grant persistent access to user exchange accounts (Coinbase, Binance) and should be encrypted at rest.

**Current state**: `IntegrationToken.token_id` is a plain `CharField`
**Goal**: Encrypt `token_id` at rest while preserving lookup capability

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    IntegrationToken                         │
├─────────────────────────────────────────────────────────────┤
│ token_id_hash   VARCHAR(64)  [indexed, searchable]         │
│ token_id_enc    BLOB         [encrypted, not searchable]   │
│ integration_type VARCHAR(64) [indexed]                     │
│ user_id         VARCHAR(255) [indexed]                     │
│ ...                                                         │
└─────────────────────────────────────────────────────────────┘

Lookup flow:
1. hash(token_id) → query token_id_hash
2. Decrypt token_id_enc to verify/use

Storage flow:
1. Store hash(token_id) in token_id_hash
2. Store encrypt(token_id) in token_id_enc
```

---

## Flow Diagrams

### Store Token Flow

```mermaid
flowchart TD
    A[token_id from Mesh] --> B{Process}
    B --> C[SHA-256 Hash]
    B --> D[Fernet Encrypt]
    C --> E[token_id_hash<br/>64-char hex]
    D --> F[token_id_enc<br/>encrypted blob]
    E --> G[(SQLite)]
    F --> G

    style A fill:#e1f5fe
    style G fill:#fff3e0
    style E fill:#c8e6c9
    style F fill:#ffcdd2
```

### Get Token Flow

```mermaid
flowchart TD
    A[Input: token_id] --> B[SHA-256 Hash]
    B --> C[token_id_hash]
    C --> D[(SQLite Query<br/>WHERE token_id_hash = ?)]
    D --> E[token_id_enc]
    E --> F[Fernet Decrypt]
    G[FERNET_KEYS] --> F
    F --> H[Decrypted token_id]

    style A fill:#e1f5fe
    style D fill:#fff3e0
    style H fill:#c8e6c9
    style G fill:#fce4ec
```

### Data Migration Flow

```mermaid
flowchart TD
    subgraph M1[Migration 0003]
        A1[ADD token_id_hash VARCHAR]
        A2[ADD token_id_enc BLOB]
    end

    subgraph M2[Migration 0004]
        B1[FOR each token]
        B2[hash token_id → token_id_hash]
        B3[encrypt token_id → token_id_enc]
        B1 --> B2 --> B3
    end

    subgraph M3[Migration 0005]
        C1[DROP token_id column]
        C2[SET token_id_hash NOT NULL]
        C3[UPDATE unique constraint]
        C1 --> C2 --> C3
    end

    M1 --> M2 --> M3

    style M1 fill:#e3f2fd
    style M2 fill:#fff8e1
    style M3 fill:#fce4ec
```

### Key Rotation Flow

```mermaid
flowchart TD
    subgraph Decrypt
        D1[token_id_enc] --> D2{Try KEY_NEW}
        D2 -->|Success| D3[Done]
        D2 -->|Fail| D4{Try KEY_OLD}
        D4 -->|Success| D3
        D4 -->|Fail| D5[Error]
    end

    subgraph Encrypt
        E1[token_id] --> E2[KEY_NEW<br/>always first key]
        E2 --> E3[token_id_enc]
    end

    style D3 fill:#c8e6c9
    style D5 fill:#ffcdd2
    style E2 fill:#e1f5fe
```

### Complete System Overview

```mermaid
flowchart LR
    subgraph Mesh[Mesh API]
        M1[integrationConnected<br/>event]
        M2[Mesh Link SDK]
    end

    subgraph App[Your Application]
        A1[storage.py]
        A2[SHA-256 + Fernet]
    end

    subgraph DB[Database]
        D1[(IntegrationToken)]
        D2[hash: indexed ●]
        D3[enc: encrypted 🔒]
    end

    M1 -->|tokenId| A1
    A1 --> A2
    A2 -->|store| D1
    D1 --> D2
    D1 --> D3
    D1 -->|retrieve| A2
    A2 -->|decrypted| A1
    A1 -->|accountTokens| M2

    style Mesh fill:#e3f2fd
    style App fill:#fff8e1
    style DB fill:#fce4ec
```

---

## Implementation Plan

### Phase 1: Add Encryption Infrastructure

**1.1 Add dependency**
```toml
# pyproject.toml - add to [project.optional-dependencies] django
"django-fernet-fields>=0.6",
```

**1.2 Configure encryption key**
```python
# settings.py
import os

# Separate key for field encryption (NOT the same as SECRET_KEY)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEYS = [os.environ.get('FIELD_ENCRYPTION_KEY', 'CHANGE_ME_IN_PROD')]
```

**1.3 Create encrypted field wrapper**
```python
# meshsbox/fields.py
from fernet_fields import EncryptedTextField
import hashlib

def token_hash(token_id: str) -> str:
    """SHA-256 hash for searchable index (first 64 chars)."""
    return hashlib.sha256(token_id.encode()).hexdigest()
```

---

### Phase 2: Model Migration

**2.1 Add new encrypted fields (migration 0003)**
```python
# IntegrationToken model changes
from fernet_fields import EncryptedTextField

class IntegrationToken(models.Model):
    # New: searchable hash index
    token_id_hash = models.CharField(max_length=64, db_index=True, null=True)

    # New: encrypted storage
    token_id_enc = EncryptedTextField(null=True)

    # Keep old field during migration
    token_id = models.CharField(max_length=255, db_index=True)  # DEPRECATED
```

**2.2 Data migration script (migration 0004)**
```python
def migrate_tokens(apps, schema_editor):
    """Encrypt existing tokens and populate hash."""
    IntegrationToken = apps.get_model('meshsbox', 'IntegrationToken')
    for token in IntegrationToken.objects.all():
        token.token_id_hash = token_hash(token.token_id)
        token.token_id_enc = token.token_id  # fernet_fields encrypts on save
        token.save()
```

**2.3 Remove old field (migration 0005)**
- Drop `token_id` column
- Make `token_id_hash` non-nullable
- Update unique constraint to use `token_id_hash`

---

### Phase 3: Update Storage API

**3.1 Update storage.py functions**
```python
def store_token(token_id: str, ...):
    """Store with encryption."""
    IntegrationToken.objects.update_or_create(
        token_id_hash=token_hash(token_id),
        integration_type=integration_type,
        defaults={
            'token_id_enc': token_id,  # Auto-encrypted by field
            ...
        }
    )

def get_token(token_id: str, ...):
    """Lookup by hash, return decrypted."""
    return IntegrationToken.objects.filter(
        token_id_hash=token_hash(token_id)
    ).first()
```

**3.2 Add property for transparent access**
```python
class IntegrationToken(models.Model):
    @property
    def token_id(self) -> str:
        """Decrypted token ID for API use."""
        return self.token_id_enc
```

---

### Phase 4: Key Management

**4.1 Environment variable setup**
```bash
# .env or environment
FIELD_ENCRYPTION_KEY=<base64-fernet-key>
```

**4.2 Key rotation support** (future)
```python
# settings.py - Fernet supports key rotation
FERNET_KEYS = [
    os.environ.get('FIELD_ENCRYPTION_KEY'),      # Current key
    os.environ.get('FIELD_ENCRYPTION_KEY_OLD'),  # Previous key (for decryption only)
]
```

---

## File Changes Summary

| File | Change |
|------|--------|
| `pyproject.toml` | Add `django-fernet-fields` dependency |
| `meshc_django/meshc_django/settings.py` | Add `FERNET_KEYS` config |
| `meshc_django/meshsbox/fields.py` | NEW: `token_hash()` utility |
| `meshc_django/meshsbox/models.py` | Add encrypted fields, deprecate old |
| `meshc_django/meshsbox/migrations/0003_*.py` | Add new fields |
| `meshc_django/meshsbox/migrations/0004_*.py` | Data migration |
| `meshc_django/meshsbox/migrations/0005_*.py` | Remove old field |
| `src/meshc/storage.py` | Update API to use hash lookups |

---

## Security Considerations

1. **Key separate from SECRET_KEY**: Encryption key is independent, can rotate without breaking sessions
2. **Hash for lookups**: SHA-256 allows O(1) lookups without exposing token values
3. **At-rest encryption**: Fernet uses AES-128-CBC with HMAC verification
4. **No logging of tokens**: Ensure decrypted values never appear in logs

---

## Testing Plan

1. Unit test: encrypt/decrypt round-trip
2. Unit test: hash lookup returns correct token
3. Migration test: existing tokens migrated correctly
4. Integration test: full store → get → revoke flow

---

## Rollback Plan

If issues arise:
1. Keep old `token_id` field until migration verified
2. Add feature flag to switch between encrypted/plaintext paths
3. Data migration is reversible (decrypt all, restore old column)
