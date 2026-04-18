"""EIP-712 signing for Polymarket CLOB V2.

Two separate EIP-712 domains are used:

1. **Exchange domain** — used for signing Orders placed on the CLOB.
   V2 bumps this domain's `version` from "1" to "2" and the verifyingContract
   points at the new V2 exchange addresses.

2. **ClobAuthDomain** — used for the L1 API key derivation handshake.
   V2 LEAVES this domain at `version` "1" — a common pitfall when migrating.

This module handles both, from scratch, using eth_account (no Polymarket SDK
dependency). Useful as a reference for anyone building their own V2 client.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data

from .constants import (
    CLOB_AUTH_DOMAIN_NAME,
    CLOB_AUTH_DOMAIN_VERSION,
    POLYGON_CHAIN_ID,
    V2_EXCHANGE_DOMAIN_NAME,
    V2_EXCHANGE_DOMAIN_VERSION,
    V2_NEG_RISK_EXCHANGE,
    V2_NEG_RISK_EXCHANGE_DOMAIN_NAME,
    V2_NEG_RISK_DOMAIN_VERSION,
    V2_STANDARD_EXCHANGE,
)
from .order import V2Order


# ── EIP-712 type definitions ────────────────────────────────────────────────

ORDER_EIP712_TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"},
    ],
    "Order": [
        {"name": "salt", "type": "uint256"},
        {"name": "maker", "type": "address"},
        {"name": "signer", "type": "address"},
        {"name": "tokenId", "type": "uint256"},
        {"name": "makerAmount", "type": "uint256"},
        {"name": "takerAmount", "type": "uint256"},
        {"name": "side", "type": "uint8"},
        {"name": "signatureType", "type": "uint8"},
        # V2-specific fields (replacing V1 nonce/expiration/taker/feeRateBps):
        {"name": "timestamp", "type": "uint256"},
        {"name": "metadata", "type": "bytes32"},
        {"name": "builder", "type": "bytes32"},
    ],
}

CLOB_AUTH_EIP712_TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
    ],
    "ClobAuth": [
        {"name": "address", "type": "address"},
        {"name": "timestamp", "type": "string"},
        {"name": "nonce", "type": "uint256"},
        {"name": "message", "type": "string"},
    ],
}


# ── Exchange Order signing ──────────────────────────────────────────────────

def build_exchange_domain(*, neg_risk: bool = False) -> dict[str, Any]:
    """Build the EIP-712 domain dict for the V2 exchange.

    Args:
        neg_risk: If True, use the NegRisk exchange domain.
                  Otherwise, use the standard CTF Exchange.
    """
    if neg_risk:
        return {
            "name": V2_NEG_RISK_EXCHANGE_DOMAIN_NAME,
            "version": V2_NEG_RISK_DOMAIN_VERSION,   # "2"
            "chainId": POLYGON_CHAIN_ID,
            "verifyingContract": V2_NEG_RISK_EXCHANGE,
        }
    return {
        "name": V2_EXCHANGE_DOMAIN_NAME,
        "version": V2_EXCHANGE_DOMAIN_VERSION,       # "2"
        "chainId": POLYGON_CHAIN_ID,
        "verifyingContract": V2_STANDARD_EXCHANGE,
    }


def sign_order(order: V2Order, private_key: str, *, neg_risk: bool = False) -> str:
    """Sign a V2 Order with the maker's EOA private key.

    Returns a 0x-prefixed hex signature suitable for the `signature` API field.
    """
    domain = build_exchange_domain(neg_risk=neg_risk)
    typed_data = {
        "types": ORDER_EIP712_TYPES,
        "primaryType": "Order",
        "domain": domain,
        "message": order.to_signable_dict(),
    }
    signable = encode_typed_data(full_message=typed_data)
    signed = Account.sign_message(signable, private_key=private_key)
    return signed.signature.hex() if signed.signature.startswith("0x") else "0x" + signed.signature.hex()


# ── L1 API auth signing (ClobAuth) ──────────────────────────────────────────

def build_clob_auth_domain() -> dict[str, Any]:
    """Build the ClobAuth domain — NOTE: version stays at '1' even in V2."""
    return {
        "name": CLOB_AUTH_DOMAIN_NAME,
        "version": CLOB_AUTH_DOMAIN_VERSION,   # "1" (unchanged in V2)
        "chainId": POLYGON_CHAIN_ID,
    }


def sign_clob_auth(
    address: str,
    timestamp: str,
    nonce: int,
    message: str,
    private_key: str,
) -> str:
    """Sign the L1 API-key derivation handshake.

    This is used once to derive your API key credentials (api_key / secret /
    passphrase). After that, L2 API calls use HMAC with those credentials.
    """
    typed_data = {
        "types": CLOB_AUTH_EIP712_TYPES,
        "primaryType": "ClobAuth",
        "domain": build_clob_auth_domain(),
        "message": {
            "address": address,
            "timestamp": timestamp,
            "nonce": nonce,
            "message": message,
        },
    }
    signable = encode_typed_data(full_message=typed_data)
    signed = Account.sign_message(signable, private_key=private_key)
    sig = signed.signature.hex()
    return sig if sig.startswith("0x") else "0x" + sig


# ── Pitfall prevention ──────────────────────────────────────────────────────

def assert_versions_correct() -> None:
    """Runtime check — easy to import into tests to prove your domain versions
    are correct. This is the single biggest pitfall in the V2 migration.
    """
    assert V2_EXCHANGE_DOMAIN_VERSION == "2", (
        "Exchange domain version must be '2' in V2"
    )
    assert CLOB_AUTH_DOMAIN_VERSION == "1", (
        "ClobAuthDomain version must stay at '1' in V2 — do not bump it"
    )
    assert V2_NEG_RISK_DOMAIN_VERSION == "2", (
        "NegRisk Exchange domain version must be '2' in V2"
    )
