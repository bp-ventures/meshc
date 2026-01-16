"""meshc: Mesh Connect deposit flow library and CLI."""

from .config import MeshConfigError, load_config
from .core import (
    AccountToken,
    ExchangeDepositAddress,
    LinkToken,
    MeshAPIError,
    MeshError,
    Network,
    ToAddress,
    TransferStatus,
    create_link_token,
    create_sandbox_cex_token,
    create_sandbox_wallet_token,
    get_account_tokens_for_user,
    get_exchange_deposit_address,
    get_networks,
    get_transfer_status,
    print_sandbox_instructions,
    simulate_deposit,
)
from .errors import (
    ERROR_DESCRIPTIONS,
    ExecuteTransferError,
    IneligibilityReason,
    PreviewTransferError,
    TransferStatus as TransferStatusEnum,
    get_error_description,
    is_retryable_error,
    requires_user_action,
)
from .storage import (
    IntegrationToken,
    delete_token,
    get_token,
    list_tokens,
    revoke_token,
    store_token,
)

__version__ = "0.1.0"

__all__ = [
    # Config
    "load_config",
    "MeshConfigError",
    # Core functions
    "create_link_token",
    "create_sandbox_cex_token",
    "create_sandbox_wallet_token",
    "get_transfer_status",
    "get_networks",
    "get_exchange_deposit_address",
    "print_sandbox_instructions",
    "simulate_deposit",
    "get_account_tokens_for_user",
    # Data classes
    "ToAddress",
    "TransferStatus",
    "LinkToken",
    "Network",
    "AccountToken",
    "ExchangeDepositAddress",
    # Exceptions
    "MeshError",
    "MeshAPIError",
    # Errors
    "ERROR_DESCRIPTIONS",
    "ExecuteTransferError",
    "IneligibilityReason",
    "PreviewTransferError",
    "TransferStatusEnum",
    "get_error_description",
    "is_retryable_error",
    "requires_user_action",
    # Token storage (MMT)
    "IntegrationToken",
    "store_token",
    "get_token",
    "list_tokens",
    "revoke_token",
    "delete_token",
]
