"""Mesh API error codes and descriptions.

Based on Mesh error dictionary documentation.
"""
from __future__ import annotations

from enum import Enum


class IneligibilityReason(str, Enum):
    """Reasons why holdings cannot be transferred."""

    NO_ELIGIBLE_NETWORKS = "NoEligibleNetworks"
    SYMBOL_DOES_NOT_MATCH = "SymbolDoesNotMatch"
    NOT_SUPPORTED_FOR_TRANSFER_BY_TARGET = "NotSupportedForTransferByTarget"
    NOT_SUPPORTED_FOR_TRANSFER_BY_SOURCE = "NotSupportedForTransferBySource"
    AMOUNT_NOT_SUFFICIENT = "AmountNotSufficient"
    NO_TARGET_NETWORK_FOUND = "NoTargetNetworkFound"
    GAS_FEE_ASSET_BALANCE_NOT_ENOUGH = "GasFeeAssetBalanceNotEnough"


class PreviewTransferError(str, Enum):
    """Preview transfer error codes."""

    NETWORK_ID_MISSING = "NetworkIdMissing"
    ADDRESS_MISSING = "AddressMissing"
    SYMBOL_MISSING = "SymbolMissing"
    UNSUPPORTED_SYMBOL_BY_NETWORK = "UnsupportedSymbolByNetwork"
    INVALID_ADDRESS_PATTERN = "InvalidAddressPattern"
    NETWORK_NOT_FOUND = "NetworkNotFound"
    NETWORK_DISABLED = "NetworkDisabled"
    INSUFFICIENT_FUNDS = "InsufficientFunds"
    INSUFFICIENT_FEE_FUNDS = "InsufficientFeeFunds"
    EMPTY_WALLET_SYMBOL_BALANCE = "EmptyWalletSymbolBalance"
    KYC_REQUIRED = "KycRequired"
    DEPOSIT_AMOUNT_TOO_LOW = "DepositAmountTooLow"
    PRICE_NOT_FOUND = "PriceNotFound"
    AMOUNT_MORE_THAN_WITHDRAW_MAXIMUM = "AmountMoreThanWithdrawMaximum"
    AMOUNT_LESS_THAN_WITHDRAW_MINIMUM = "AmountLessThanWithdrawMinimum"


class ExecuteTransferError(str, Enum):
    """Execute transfer error codes."""

    PREVIEW_EXPIRED = "PreviewExpired"
    TRANSFER_IS_REQUESTED = "TransferIsRequested"
    PREVIEW_NOT_FOUND = "PreviewNotFound"
    ADDRESS_NOT_REGISTERED = "AddressNotRegistered"


class TransferStatus(str, Enum):
    """Transfer execution statuses."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    MFA_REQUIRED = "mfaRequired"
    EMAIL_CONFIRMATION_REQUIRED = "emailConfirmationRequired"
    DEVICE_CONFIRMATION_REQUIRED = "deviceConfirmationRequired"
    MFA_FAILED = "mfaFailed"
    ADDRESS_WHITELIST_REQUIRED = "addressWhitelistRequired"


# Human-readable error descriptions
ERROR_DESCRIPTIONS: dict[str, str] = {
    # Ineligibility reasons
    "NoEligibleNetworks": (
        "None of the networks supported by source and target accounts can be used. "
        "Check that both sides support a common network."
    ),
    "SymbolDoesNotMatch": "The requested symbol differs from the holding's symbol.",
    "NotSupportedForTransferByTarget": (
        "The target does not support receiving this token on any eligible network."
    ),
    "NotSupportedForTransferBySource": (
        "The source does not support sending this token on any eligible network."
    ),
    "AmountNotSufficient": "Amount + gas fee exceeds available balance.",
    "NoTargetNetworkFound": "Target address does not support this network.",
    "GasFeeAssetBalanceNotEnough": (
        "Token balance is sufficient, but not enough native asset for gas fees "
        "(e.g., need ETH to send USDC)."
    ),
    # Preview errors
    "NetworkIdMissing": "networkId field was not provided in toAddresses.",
    "AddressMissing": "address field was not provided in toAddresses.",
    "SymbolMissing": "symbol field was not provided in toAddresses.",
    "UnsupportedSymbolByNetwork": "This network does not support the requested token.",
    "InvalidAddressPattern": "Address format doesn't match the network's pattern.",
    "NetworkNotFound": "The specified network ID does not exist.",
    "NetworkDisabled": "This network is temporarily disabled.",
    "InsufficientFunds": "Not enough token balance for this transfer.",
    "InsufficientFeeFunds": "Not enough balance to cover transfer fees.",
    "EmptyWalletSymbolBalance": "Source wallet has zero balance of this token.",
    "KycRequired": "The account requires KYC verification to perform transfers.",
    "DepositAmountTooLow": "Amount is below the minimum accepted by the target.",
    "PriceNotFound": "Could not fetch current price for this asset.",
    "AmountMoreThanWithdrawMaximum": "Amount exceeds the maximum withdrawal limit.",
    "AmountLessThanWithdrawMinimum": "Amount is below the minimum withdrawal limit.",
    # Execute errors
    "PreviewExpired": "The transfer preview has expired. Request a new one.",
    "TransferIsRequested": "This transfer has already been requested.",
    "PreviewNotFound": "Could not find the transfer preview.",
    "AddressNotRegistered": "The target address is not registered/whitelisted.",
}


def get_error_description(error_code: str) -> str:
    """Get human-readable description for an error code."""
    return ERROR_DESCRIPTIONS.get(error_code, f"Unknown error: {error_code}")


def is_retryable_error(error_code: str) -> bool:
    """Check if an error might succeed on retry."""
    retryable = {
        "PreviewExpired",
        "PriceNotFound",
        "NetworkDisabled",  # might be temporary
    }
    return error_code in retryable


def requires_user_action(error_code: str) -> bool:
    """Check if error requires user intervention."""
    user_action = {
        "KycRequired",
        "InsufficientFunds",
        "InsufficientFeeFunds",
        "GasFeeAssetBalanceNotEnough",
        "AmountNotSufficient",
        "AddressNotRegistered",
    }
    return error_code in user_action
