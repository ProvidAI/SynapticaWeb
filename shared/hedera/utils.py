"""Utility helpers for working with Hedera account identifiers."""

from __future__ import annotations

import re
from typing import Final

from web3 import Web3

_ACCOUNT_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d+\.\d+\.\d+$")


def hedera_account_to_evm_address(value: str) -> str:
    """
    Convert a Hedera account identifier or raw hex string into a checksum EVM address.

    Args:
        value: Hedera account ID (e.g. '0.0.1234'), 0x-prefixed EVM address, or 40-char hex string.

    Returns:
        Canonical checksum EVM address.

    Raises:
        ValueError: If the input cannot be converted into a valid address.
    """
    candidate = (value or "").strip()
    if not candidate:
        raise ValueError("Account identifier cannot be empty")

    # Already an 0x-prefixed hex value.
    if candidate.startswith(("0x", "0X")):
        return Web3.to_checksum_address(candidate)

    # Raw 40 character hex value without 0x prefix.
    if len(candidate) == 40 and _is_hex(candidate):
        return Web3.to_checksum_address(f"0x{candidate}")

    # Hedera account identifier in shard.realm.num format.
    if _ACCOUNT_ID_PATTERN.match(candidate):
        shard_str, realm_str, num_str = candidate.split(".")
        try:
            shard = int(shard_str)
            realm = int(realm_str)
            num = int(num_str)
        except ValueError as exc:
            raise ValueError(f"Invalid Hedera account components in '{candidate}'") from exc

        solidity = f"{shard:08x}{realm:016x}{num:016x}"
        return Web3.to_checksum_address(f"0x{solidity}")

    raise ValueError(f"Unsupported Hedera account identifier format: '{value}'")


def _is_hex(value: str) -> bool:
    try:
        int(value, 16)
        return True
    except ValueError:
        return False
