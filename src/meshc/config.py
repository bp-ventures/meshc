"""Configuration loading for meshc.

Priority (highest to lowest):
1. Function arguments
2. Environment variables
3. local_settings.py in current directory
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("meshc")

SANDBOX_API_URL = "https://sandbox-integration-api.meshconnect.com"
PRODUCTION_API_URL = "https://integration-api.meshconnect.com"

# Network IDs (static per Mesh documentation)
DEFAULT_STELLAR_NETWORK_ID = "06855704-43d2-4ad2-a73c-372f0c3534e1"
SEPOLIA_NETWORK_ID = "03b2d786-7092-4a6a-9737-d6013e21819b"  # Ethereum Sepolia testnet

# Sandbox testing: CEX uses mock data, wallet uses Sepolia testnet
SANDBOX_TEST_NETWORKS = {
    "stellar": DEFAULT_STELLAR_NETWORK_ID,
    "sepolia": SEPOLIA_NETWORK_ID,
}


class MeshConfigError(Exception):
    """Configuration missing or invalid."""


def get_token_db_path() -> Path:
    """Get token database path from configuration.

    Priority: env var > local_settings.py > default (~/.meshc/tokens.db)

    Returns:
        Path to SQLite database file
    """
    db_path = (
        _get_env("MESHC_TOKEN_DB")
        or _load_local_settings().get("MESHC_TOKEN_DB")
        or str(Path.home() / ".meshc" / "tokens.db")
    )
    return Path(db_path).expanduser()


def init_token_storage() -> None:
    """Initialize token storage database.

    Creates database and tables if they don't exist.
    Safe to call multiple times (idempotent).
    """
    try:
        from .storage import init_db
    except ImportError as e:
        logger.warning("storage module not available: %s", e)
        return

    db_path = get_token_db_path()
    init_db(db_path)
    logger.debug("token storage ready at %s", db_path)


def _load_local_settings() -> dict[str, Any]:
    """Load settings from local_settings.py.

    Search order:
    1. Current working directory
    2. Parent directories (up to 3 levels, for Django apps in subdirs)
    """
    # Search cwd and up to 3 parent directories
    search_dirs = [Path.cwd()]
    for i in range(1, 4):
        parent = Path.cwd().parents[i - 1] if i <= len(Path.cwd().parents) else None
        if parent:
            search_dirs.append(parent)

    settings_path = None
    for search_dir in search_dirs:
        candidate = search_dir / "local_settings.py"
        if candidate.is_file():
            settings_path = candidate
            break

    if settings_path is None:
        return {}

    # Import the module
    import importlib.util

    spec = importlib.util.spec_from_file_location("local_settings", settings_path)
    if spec is None or spec.loader is None:
        return {}

    try:
        module = importlib.util.module_from_spec(spec)
        sys.modules["local_settings"] = module
        spec.loader.exec_module(module)
        logger.debug("loaded settings from %s", settings_path)

        # Extract uppercase attributes (Django convention)
        return {
            k: getattr(module, k)
            for k in dir(module)
            if k.isupper() and not k.startswith("_")
        }
    except Exception as e:
        logger.warning("failed to load local_settings.py: %s", e)
        return {}


def _get_env(key: str) -> str | None:
    """Get environment variable, return None if empty."""
    val = os.environ.get(key, "").strip()
    return val if val else None


def load_config(
    client_id: str | None = None,
    client_secret: str | None = None,
    api_url: str | None = None,
    stellar_network_id: str | None = None,
    require_credentials: bool = True,
) -> dict[str, Any]:
    """
    Load configuration from multiple sources.

    Priority: arguments > env vars > local_settings.py

    Args:
        client_id: Mesh client ID
        client_secret: Mesh client secret
        api_url: Mesh API URL (defaults to sandbox)
        stellar_network_id: Stellar network ID
        require_credentials: Raise if credentials missing

    Returns:
        Merged configuration dict

    Raises:
        MeshConfigError: If required values missing
    """
    local = _load_local_settings()

    config: dict[str, Any] = {
        "client_id": (
            client_id
            or _get_env("MESH_CLIENT_ID")
            or local.get("MESH_CLIENT_ID")
        ),
        "client_secret": (
            client_secret
            or _get_env("MESH_CLIENT_SECRET")
            or _get_env("MESH_SECRET")  # alternate name
            or local.get("MESH_CLIENT_SECRET")
            or local.get("MESH_SECRET")
        ),
        "api_url": (
            api_url
            or _get_env("MESH_API_URL")
            or _get_env("MESH_API")  # alternate name
            or local.get("MESH_API_URL")
            or local.get("MESH_API")
            or SANDBOX_API_URL
        ),
        "stellar_network_id": (
            stellar_network_id
            or _get_env("MESH_STELLAR_NETWORK_ID")
            or local.get("MESH_STELLAR_NETWORK_ID")
            or DEFAULT_STELLAR_NETWORK_ID
        ),
        "transfer_type": local.get("MESH_TRANSFER_TYPE", "deposit"),
        "enable_smart_funding": local.get("MESH_ENABLE_SMART_FUNDING", True),
    }

    if require_credentials:
        if not config["client_id"]:
            raise MeshConfigError(
                "MESH_CLIENT_ID not set. "
                "Set via env var, local_settings.py, or --client-id"
            )
        if not config["client_secret"]:
            raise MeshConfigError(
                "MESH_CLIENT_SECRET not set. "
                "Set via env var, local_settings.py, or --client-secret"
            )

    return config


def mask_secret(secret: str | None) -> str:
    """Mask a secret for safe logging."""
    if not secret:
        return "<not set>"
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


def setup_api_logger(log_dir: Path | None = None) -> logging.Logger:
    """Configure dedicated logger for Mesh API audit trail.

    Logs to ~/.meshc/mesh_api.log with daily rotation.
    Old logs are compressed with gzip and kept forever.
    """
    import gzip
    import shutil
    from logging.handlers import TimedRotatingFileHandler

    api_logger = logging.getLogger("meshc.api")

    if api_logger.handlers:  # Already configured
        return api_logger

    log_dir = log_dir or Path.home() / ".meshc"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "mesh_api.log"

    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=0,  # Keep forever
        encoding="utf-8",
    )

    # Compress rotated logs with gzip
    def namer(name: str) -> str:
        return name + ".gz"

    def rotator(source: str, dest: str) -> None:
        with open(source, "rb") as f_in:
            with gzip.open(dest, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        Path(source).unlink()

    handler.namer = namer
    handler.rotator = rotator

    handler.setFormatter(logging.Formatter(
        "%(levelname)s %(asctime)s %(name)s %(filename)s:%(lineno)d %(funcName)s() :: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    api_logger.addHandler(handler)
    api_logger.setLevel(logging.INFO)
    api_logger.propagate = False  # Don't duplicate to root logger

    return api_logger
