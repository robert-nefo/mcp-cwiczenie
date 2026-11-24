#!/usr/bin/env python3
"""IPv4 subnet calculator (standard library only).

Usage:
    python3 subnet.py CIDR [--split /N]

Example:
    python3 subnet.py 10.0.50.203/24 --split /26

Special cases handled explicitly:
- /31 point-to-point links (RFC 3021): both addresses are usable hosts;
- /32: a single address.

The pure logic lives in :func:`calculate` and :func:`split`; command-line
argument handling stays in :func:`main`.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys

__all__ = ["calculate", "split", "main"]


def _require_network(cidr: str) -> ipaddress.IPv4Network:
    """Parse *cidr* as an IPv4 network, raising ``ValueError`` otherwise."""
    if not isinstance(cidr, str) or "/" not in cidr:
        raise ValueError(
            f"expected CIDR notation '<ip>/<prefix>', e.g. '10.0.50.0/24', got {cidr!r}"
        )
    try:
        network = ipaddress.ip_network(cidr.strip(), strict=False)
    except ValueError as exc:
        raise ValueError(f"invalid CIDR {cidr!r}: {exc}") from exc
    if not isinstance(network, ipaddress.IPv4Network):
        raise ValueError(f"only IPv4 networks are supported, got {cidr!r}")
    return network


def _wildcard(network: ipaddress.IPv4Network) -> str:
    """Bitwise inverse of the subnet mask, as a dotted quad."""
    inverted = int(network.netmask) ^ 0xFFFFFFFF
    return str(ipaddress.IPv4Address(inverted))


def calculate(cidr: str) -> dict:
    """Compute subnet parameters for a single CIDR network.

    Args:
        cidr: IPv4 address in CIDR notation, e.g. ``"10.0.50.203/24"``.
            Host bits are ignored; the containing network is used
            (``10.0.50.203/24`` -> network ``10.0.50.0/24``).

    Returns:
        A dict with these keys:

        - ``network``:         network address (e.g. ``"10.0.50.0"``)
        - ``prefix``:          prefix length (int)
        - ``mask``:            subnet mask (e.g. ``"255.255.255.0"``)
        - ``wildcard``:        inverted mask (e.g. ``"0.0.0.255"``)
        - ``broadcast``:       last address of the network range
        - ``first_host``:      first address usable by hosts
        - ``last_host``:       last address usable by hosts
        - ``usable_hosts``:    number of addresses usable by hosts:
                               ``/31`` -> 2 (RFC 3021), ``/32`` -> 1,
                               otherwise total - 2 (network and broadcast
                               addresses are excluded)
        - ``total_addresses``: all addresses in the range
        - ``is_private``:      True if the network lies in a private range

    Raises:
        ValueError: if *cidr* is not a valid IPv4 CIDR.
    """
    network = _require_network(cidr)
    first = int(network.network_address)
    last = int(network.broadcast_address)
    total = network.num_addresses

    if network.prefixlen == 32:
        first_host = last_host = network.network_address
        usable = 1
    elif network.prefixlen == 31:
        # RFC 3021: both addresses are usable hosts, there is no
        # separate network/broadcast address.
        first_host = network.network_address
        last_host = network.broadcast_address
        usable = 2
    else:
        first_host = ipaddress.IPv4Address(first + 1)
        last_host = ipaddress.IPv4Address(last - 1)
        usable = total - 2

    return {
        "network": str(network.network_address),
        "prefix": network.prefixlen,
        "mask": str(network.netmask),
        "wildcard": _wildcard(network),
        "broadcast": str(network.broadcast_address),
        "first_host": str(first_host),
        "last_host": str(last_host),
        "usable_hosts": usable,
        "total_addresses": total,
        "is_private": network.is_private,
    }


def _parse_prefix(value) -> int:
    """Coerce a prefix given as int, ``"26"`` or ``"/26"`` into an int."""
    if isinstance(value, str):
        value = value.strip().lstrip("/")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid prefix {value!r}: expected an integer") from exc


def split(cidr: str, new_prefix) -> list[str]:
    """Split a CIDR network into smaller subnets.

    Args:
        cidr: IPv4 network in CIDR notation, e.g. ``"10.0.50.0/24"``.
        new_prefix: target prefix length (int, ``"26"`` or ``"/26"``);
            must be longer than the original prefix.

    Returns:
        A list of CIDR strings of the resulting subnets:
        ``2 ** (new_prefix - original_prefix)`` of them, e.g.
        ``split("10.0.50.0/24", 26)`` ->
        ``["10.0.50.0/26", "10.0.50.64/26", "10.0.50.128/26", "10.0.50.192/26"]``

    Raises:
        ValueError: on invalid input, or when *new_prefix* is not longer
            than the original prefix (cannot split into larger networks).
    """
    network = _require_network(cidr)
    prefix = _parse_prefix(new_prefix)
    if prefix > 32:
        raise ValueError(f"prefix must be between 0 and 32, got {prefix}")
    if prefix <= network.prefixlen:
        raise ValueError(
            f"new prefix {prefix} must be longer than the original "
            f"{network.prefixlen} to split {network} into smaller subnets"
        )
    return [str(subnet) for subnet in network.subnets(new_prefix=prefix)]


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point: ``subnet.py CIDR [--split /N]``."""
    parser = argparse.ArgumentParser(
        prog="subnet.py",
        description="IPv4 subnet calculator; prints network parameters as JSON.",
    )
    parser.add_argument("cidr", help="address in CIDR notation, e.g. 10.0.50.203/24")
    parser.add_argument(
        "--split",
        metavar="PREFIX",
        default=None,
        help="split the network into subnets with this prefix, e.g. /26",
    )
    args = parser.parse_args(argv)

    try:
        result: dict = {"network": calculate(args.cidr)}
        if args.split is not None:
            subnets = split(args.cidr, args.split)
            result["split"] = {
                "new_prefix": _parse_prefix(args.split),
                "count": len(subnets),
                "subnets": subnets,
            }
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
