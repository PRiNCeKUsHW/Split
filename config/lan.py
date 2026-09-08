"""Discover the addresses this machine answers to on the flat's WiFi."""

from __future__ import annotations

import socket


def lan_hosts() -> list[str]:
    """Return hostnames and IPv4 addresses usable to reach this machine.

    Django's ALLOWED_HOSTS has no wildcard form for ``192.168.*``, so rather
    than guessing a subnet we detect the real addresses at startup. Everything
    here degrades quietly: on a laptop with no network at all this still
    returns loopback, and the app still serves.
    """
    hosts: set[str] = {"127.0.0.1", "localhost", "0.0.0.0"}

    try:
        hostname = socket.gethostname()
        hosts.add(hostname)
        hosts.add(f"{hostname}.local")
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            hosts.add(info[4][0])
    except OSError:
        pass

    # Ask the routing table which interface would reach the outside world.
    # A UDP connect() sends no packets, so this works with no internet present.
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            hosts.add(probe.getsockname()[0])
        finally:
            probe.close()
    except OSError:
        pass

    return sorted(hosts)


def primary_lan_ip() -> str:
    """The address to read out to flatmates. Falls back to loopback."""
    for host in lan_hosts():
        if host.startswith(("192.168.", "10.", "172.")):
            return host
    return "127.0.0.1"
