"""Discover the machine's LAN addresses so operators can reach the dashboard.

Browsers on other devices (an iPad, a phone, a laptop) connect to one of these
addresses over the local network. Nothing is installed on those devices; they
only view the dashboard.
"""

import socket

IPAD_NOTE = (
    "Other devices (iPad, phone, laptop) only view the dashboard over your "
    "network; nothing is installed on them."
)


def local_ipv4_addresses() -> list[str]:
    """Return non-loopback, non-link-local IPv4 addresses for this machine."""
    found: set[str] = set()
    # Primary outbound interface. connect() on a UDP socket sends no packets;
    # it only selects the route the OS would use, revealing the local address.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 80))  # TEST-NET-1: reserved, never routed.
            found.add(str(probe.getsockname()[0]))
    except OSError:
        pass
    # Every address the hostname resolves to (covers additional interfaces).
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(str(info[4][0]))
    except OSError:
        pass
    return sorted(
        address
        for address in found
        if not address.startswith("127.") and not address.startswith("169.254.")
    )


def address_report(port: int) -> dict:
    """Build the local and LAN URLs for the admin console and the /display strip."""
    lan = [
        {
            "host": address,
            "admin": f"http://{address}:{port}/",
            "display": f"http://{address}:{port}/display",
        }
        for address in local_ipv4_addresses()
    ]
    return {
        "port": port,
        "localAdmin": f"http://localhost:{port}/",
        "localDisplay": f"http://localhost:{port}/display",
        "lan": lan,
        "note": IPAD_NOTE,
    }
