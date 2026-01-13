# Django Cleanup: Remove web/ Directory

**Date**: 2026-01-13

## Summary

Consolidated frontend code by removing the `web/` directory now that Django serves as the primary web UI.

---

## Changes

| Action | Item | Reason |
|--------|------|--------|
| **Moved** | `web/examples/` → `docs/front-end-examples/` | Preserve React reference implementation |
| **Deleted** | `web/link.html` | Replaced by Django template |
| **Deleted** | `web/` directory | No longer needed |
| **Removed** | `--local` flag from CLI | Django replaces local HTTP server |
| **Updated** | `docs/django-migration-1.md` | Remove stale reference |

---

## Files Modified

```
DELETED:
  web/link.html                              # 7KB - replaced by Django
  web/                                       # directory removed

MOVED:
  web/examples/react-example/ → docs/front-end-examples/react-example/

MODIFIED:
  src/meshc/cli.py                           # -40 lines (--local flag + HTTP server)
  docs/django-migration-1.md                 # Updated design decisions
```

---

## Code Removed from cli.py

The `--local` flag served `web/link.html` via a built-in HTTP server:

```python
# REMOVED: ~40 lines
if getattr(args, 'local', False):
    html_dir = pathlib.Path(__file__).parent.parent.parent / 'web'
    # ... HTTP server on port 8092
    # ... threading, socketserver, webbrowser
```

**Replacement**: Use Django at `https://meshcdev.bpventures.us/meshc/` or `localhost:10409/meshc/`

---

## Before vs After

| Feature | Before | After |
|---------|--------|-------|
| Local testing | `meshc sandbox-cex --local` | Django: `localhost:10409/meshc/` |
| Open Mesh UI | `meshc sandbox-cex --open` | `meshc sandbox-cex --open` (unchanged) |
| Web frontend | Two HTML files (duplicate JS) | Single Django template |
| React example | `web/examples/` | `docs/front-end-examples/` |

---

## Why This Matters

1. **Single source of truth** - Django is now the only web frontend
2. **Less code** - Removed 40 lines of HTTP server code from CLI
3. **No duplication** - JavaScript logic exists in one place
4. **Cleaner repo** - `web/` directory eliminated

---

## Testing

```bash
# CLI tests
pytest tests/ -v                    # 50 passed

# Django tests
cd meshc_django && python manage.py test meshsbox    # 13 passed
```
