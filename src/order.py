"""V2 Order struct + builder.

The V2 Order struct:
    Order(
        uint256 salt,
        address maker,
        address signer,
        uint256 tokenId,
        uint256 makerAmount,
        uint256 takerAmount,
        uint8 side,
        uint8 signatureType,
        uint256 timestamp,     // NEW in V2 (replaces nonce)
        bytes32 metadata,      // NEW in V2
        bytes32 builder        // NEW in V2 (embeds builder attribution)
    )

Removed from V1: nonce, expiration, taker, feeRateBps.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import asdict, dataclass, field
from decimal import Decimal

from .constants import SIDE_BUY, SIDE_SELL, SIG_TYPE_EOA, ZERO_BYTES32


# Contract decimals: 6 for USDC-style amounts, shares also scaled 6 decimals
USDC_DECIMALS = 6


def to_usdc_units(amount_usd: float) -> int:
    """Convert a USD float to on-chain integer (6 decimals)."""
    return int(Decimal(str(amount_usd)) * Decimal(10 ** USDC_DECIMALS))


def random_salt() -> int:
    """Generate a random 256-bit salt for order uniqueness."""
    return secrets.randbelow(2**256 - 1)


def current_timestamp_ms() -> int:
    """V2 uses millisecond timestamps (replaces V1 nonce)."""
    return int(time.time() * 1000)


@dataclass
class V2Order:
    """Polymarket CLOB V2 order struct — matches the on-chain Order type exactly."""

    salt: int                # random uint256 for uniqueness
    maker: str               # maker address (lowercase 0x-prefixed)
    signer: str              # signer address (same as maker for EOA)
    tokenId: int             # CLOB token ID (which outcome)
    makerAmount: int         # amount you offer (6-decimal units)
    takerAmount: int         # amount you expect in return (6-decimal units)
    side: int                # 0 = BUY, 1 = SELL
    signatureType: int       # 0 = EOA, 1 = POLY_PROXY, 2 = POLY_GNOSIS_SAFE
    timestamp: int           # milliseconds (replaces V1 nonce)
    metadata: str = ZERO_BYTES32   # bytes32 (application-defined; zero by default)
    builder: str = ZERO_BYTES32    # bytes32 builderCode; zero if no builder attribution

    def to_signable_dict(self) -> dict:
        """Dict form used for EIP-712 signing (matches struct field order)."""
        return {
            "salt": self.salt,
            "maker": self.maker,
            "signer": self.signer,
            "tokenId": self.tokenId,
            "makerAmount": self.makerAmount,
            "takerAmount": self.takerAmount,
            "side": self.side,
            "signatureType": self.signatureType,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "builder": self.builder,
        }

    def to_api_dict(self, signature: str) -> dict:
        """Form accepted by POST /order."""
        d = self.to_signable_dict()
        # API expects string versions of numeric fields
        for k in ("salt", "tokenId", "makerAmount", "takerAmount", "timestamp"):
            d[k] = str(d[k])
        d["signature"] = signature
        return d


def build_limit_buy(
    *,
    token_id: int,
    price: float,
    amount_usd: float,
    maker: str,
    signer: str | None = None,
    signature_type: int = SIG_TYPE_EOA,
    builder_code: str = ZERO_BYTES32,
) -> V2Order:
    """Build a limit BUY order buying YES shares at the given price.

    Example:
        build_limit_buy(token_id=12345..., price=0.50, amount_usd=100, maker=wallet)
        → buys 200 shares at 50¢ each.
    """
    if not (0 < price < 1):
        raise ValueError(f"Price must be in (0, 1), got {price}")
    if amount_usd <= 0:
        raise ValueError("amount_usd must be positive")

    # Shares = amount / price
    shares = amount_usd / price
    maker_amount = to_usdc_units(amount_usd)      # what you spend (USDC units)
    taker_amount = to_usdc_units(shares)          # shares you receive (same 6-decimal scale)

    return V2Order(
        salt=random_salt(),
        maker=maker.lower(),
        signer=(signer or maker).lower(),
        tokenId=token_id,
        makerAmount=maker_amount,
        takerAmount=taker_amount,
        side=SIDE_BUY,
        signatureType=signature_type,
        timestamp=current_timestamp_ms(),
        metadata=ZERO_BYTES32,
        builder=builder_code,
    )


def build_limit_sell(
    *,
    token_id: int,
    price: float,
    shares: float,
    maker: str,
    signer: str | None = None,
    signature_type: int = SIG_TYPE_EOA,
    builder_code: str = ZERO_BYTES32,
) -> V2Order:
    """Build a limit SELL order selling `shares` YES at the given price."""
    if not (0 < price < 1):
        raise ValueError(f"Price must be in (0, 1), got {price}")
    if shares <= 0:
        raise ValueError("shares must be positive")

    proceeds_usd = shares * price
    maker_amount = to_usdc_units(shares)
    taker_amount = to_usdc_units(proceeds_usd)

    return V2Order(
        salt=random_salt(),
        maker=maker.lower(),
        signer=(signer or maker).lower(),
        tokenId=token_id,
        makerAmount=maker_amount,
        takerAmount=taker_amount,
        side=SIDE_SELL,
        signatureType=signature_type,
        timestamp=current_timestamp_ms(),
        metadata=ZERO_BYTES32,
        builder=builder_code,
    )
