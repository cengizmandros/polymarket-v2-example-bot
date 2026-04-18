"""pUSD collateral wrap helper.

V2 moves collateral from USDC.e (a bridged USDC) to pUSD (Polymarket's own
ERC-20 1:1 backed by USDC). API-only traders must wrap their USDC.e → pUSD
themselves via the CollateralOnramp contract. polymarket.com handles this
automatically for UI users.

Flow:
    1. Approve USDC.e to CollateralOnramp
    2. Call CollateralOnramp.wrap(amount) — burns USDC, mints pUSD
    3. Approve pUSD to V2 exchange
    4. Now you can place orders

NOTE: as of April 2026, the Collateral Onramp address had not been made
public when this module was written. Placeholders marked TODO below must be
filled in when Polymarket publishes them. The code structure is correct.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


MINIMAL_ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

# Placeholder — will be populated by Polymarket's official docs
COLLATERAL_ONRAMP_ABI = [
    {
        "inputs": [{"name": "amount", "type": "uint256"}],
        "name": "wrap",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "amount", "type": "uint256"}],
        "name": "unwrap",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


def wrap_usdc_to_pusd(
    web3: Any,
    *,
    wallet_address: str,
    private_key: str,
    usdc_address: str,
    pusd_address: str,
    onramp_address: str,
    exchange_address: str,
    amount_usdc_units: int,
) -> list[str]:
    """Execute the full USDC → pUSD wrap flow.

    Returns a list of transaction hashes (approve, wrap, approve pUSD).

    This function SENDS ON-CHAIN TRANSACTIONS and costs gas. Test on a
    forked network first or with a small amount.
    """
    tx_hashes: list[str] = []
    account = web3.eth.account.from_key(private_key)

    usdc = web3.eth.contract(address=usdc_address, abi=MINIMAL_ERC20_ABI)
    pusd = web3.eth.contract(address=pusd_address, abi=MINIMAL_ERC20_ABI)
    onramp = web3.eth.contract(address=onramp_address, abi=COLLATERAL_ONRAMP_ABI)

    # 1. Approve USDC to CollateralOnramp
    nonce = web3.eth.get_transaction_count(wallet_address)
    approve_tx = usdc.functions.approve(onramp_address, amount_usdc_units).build_transaction({
        "from": wallet_address,
        "nonce": nonce,
        "gas": 150_000,
        "gasPrice": web3.eth.gas_price,
    })
    signed = account.sign_transaction(approve_tx)
    h1 = web3.eth.send_raw_transaction(signed.raw_transaction).hex()
    web3.eth.wait_for_transaction_receipt(h1)
    tx_hashes.append(h1)
    logger.info("Approved USDC → onramp: %s", h1)

    # 2. Call wrap()
    wrap_tx = onramp.functions.wrap(amount_usdc_units).build_transaction({
        "from": wallet_address,
        "nonce": nonce + 1,
        "gas": 250_000,
        "gasPrice": web3.eth.gas_price,
    })
    signed = account.sign_transaction(wrap_tx)
    h2 = web3.eth.send_raw_transaction(signed.raw_transaction).hex()
    web3.eth.wait_for_transaction_receipt(h2)
    tx_hashes.append(h2)
    logger.info("Wrapped USDC → pUSD: %s", h2)

    # 3. Approve pUSD to V2 exchange
    approve_pusd_tx = pusd.functions.approve(exchange_address, amount_usdc_units).build_transaction({
        "from": wallet_address,
        "nonce": nonce + 2,
        "gas": 150_000,
        "gasPrice": web3.eth.gas_price,
    })
    signed = account.sign_transaction(approve_pusd_tx)
    h3 = web3.eth.send_raw_transaction(signed.raw_transaction).hex()
    web3.eth.wait_for_transaction_receipt(h3)
    tx_hashes.append(h3)
    logger.info("Approved pUSD → exchange: %s", h3)

    return tx_hashes


def check_pusd_balance(web3: Any, pusd_address: str, wallet_address: str) -> int:
    """Query pUSD balance of a wallet (in 6-decimal units)."""
    pusd = web3.eth.contract(address=pusd_address, abi=MINIMAL_ERC20_ABI)
    return pusd.functions.balanceOf(wallet_address).call()


def check_exchange_allowance(
    web3: Any, pusd_address: str, wallet_address: str, exchange_address: str,
) -> int:
    """Check how much pUSD the exchange is approved to spend for a wallet."""
    pusd = web3.eth.contract(address=pusd_address, abi=MINIMAL_ERC20_ABI)
    return pusd.functions.allowance(wallet_address, exchange_address).call()
