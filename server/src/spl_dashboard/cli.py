"""Console entry point: ``spl-dashboard``.

Starts the LAN service with a single Uvicorn worker and prints the addresses to
open on this machine and on other devices on the same network.
"""

import argparse
import os
from pathlib import Path

from platformdirs import user_data_dir

from .addresses import IPAD_NOTE, local_ipv4_addresses

DEFAULT_PORT = 8000
# A LAN monitor is meant to be reachable across the local network by default.
DEFAULT_HOST = "0.0.0.0"


def default_data_dir() -> Path:
    """Per-user data directory (platform-appropriate), matching the service default."""
    return Path(user_data_dir("spl-dashboard", appauthor=False))


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="spl-dashboard",
        description=(
            "Run the SPL Dashboard sound monitor on this computer and serve it to "
            "browsers on your local network."
        ),
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Address to bind (default {DEFAULT_HOST}, i.e. all network interfaces).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to serve on (default {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help=(
            "Where events, configuration and calibration are stored "
            f"(default: {default_data_dir()})."
        ),
    )
    parser.add_argument("--version", action="store_true", help="Print the version and exit.")
    return parser.parse_args(argv)


def _print_banner(host: str, port: int, data_dir: Path) -> None:
    lines = ["", "  SPL Dashboard is starting.", ""]
    lines.append("  On this computer:")
    lines.append(f"    Admin console:  http://localhost:{port}/")
    lines.append(f"    Strip display:  http://localhost:{port}/display")
    addresses = local_ipv4_addresses()
    if host not in ("0.0.0.0", "::") and host not in ("localhost", "127.0.0.1"):
        # An explicit non-wildcard bind is the only reachable LAN address.
        addresses = [host]
    if addresses:
        lines.append("")
        lines.append("  From an iPad, phone or laptop on the same Wi-Fi (open /display):")
        for address in addresses:
            lines.append(f"    http://{address}:{port}/display")
    else:
        lines.append("")
        lines.append("  No LAN address detected yet; connect this computer to your network.")
    lines.append("")
    lines.append(f"  {IPAD_NOTE}")
    lines.append(f"  Data directory: {data_dir}")
    lines.append("  Press Ctrl+C to stop.")
    lines.append("")
    print("\n".join(lines), flush=True)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.version:
        from importlib.metadata import version

        print(version("spl-dashboard"))
        return

    data_dir = Path(args.data_dir).expanduser() if args.data_dir else default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    # create_app reads SPL_DATA_DIR when Uvicorn imports the app in this process.
    os.environ["SPL_DATA_DIR"] = str(data_dir)

    _print_banner(args.host, args.port, data_dir)

    import uvicorn

    uvicorn.run(
        "spl_dashboard.main:app",
        host=args.host,
        port=args.port,
        workers=1,
        log_level="info",
    )


if __name__ == "__main__":
    main()
