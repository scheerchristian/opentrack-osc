#!/usr/bin/env python3
"""
opentrack_osc.py — Forward OpenTrack UDP output to an OSC target.

OpenTrack "UDP over network" protocol:
  6 x little-endian double (8 bytes each) = 48 bytes per packet
  Order: X (mm), Y (mm), Z (mm), Yaw (°), Pitch (°), Roll (°)
"""

import socket
import struct
import sys
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # pip install tomli
    except ImportError:
        sys.exit(
            "tomllib not found. Install it with: pip install tomli  "
            "(or use Python 3.11+)"
        )

from pythonosc import udp_client
from pythonosc.osc_message_builder import OscMessageBuilder

OPENTRACK_FORMAT = "<6d"  # 6 little-endian doubles
OPENTRACK_SIZE = struct.calcsize(OPENTRACK_FORMAT)
AXIS_NAMES = ("x", "y", "z", "yaw", "pitch", "roll")


@dataclass
class Config:
    listen_host: str
    listen_port: int
    target_host: str
    target_port: int
    mode: str               # "bundle" | "individual"
    bundle_address: str
    individual_addresses: dict[str, str]
    show_values: bool


def load_config(path: Path) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    ot = raw["opentrack"]
    osc = raw["osc"]
    mapping = raw["mapping"]
    log_cfg = raw.get("logging", {})

    mode = mapping.get("mode", "bundle").lower()
    if mode not in ("bundle", "individual"):
        sys.exit(f"config: mapping.mode must be 'bundle' or 'individual', got '{mode}'")

    individual = mapping.get("individual", {})
    for axis in AXIS_NAMES:
        if axis not in individual:
            individual[axis] = f"/opentrack/{axis}"

    log_level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    return Config(
        listen_host=ot.get("listen_host", "0.0.0.0"),
        listen_port=int(ot.get("listen_port", 4242)),
        target_host=osc["target_host"],
        target_port=int(osc["target_port"]),
        mode=mode,
        bundle_address=mapping.get("bundle_address", "/opentrack/pose"),
        individual_addresses=individual,
        show_values=log_cfg.get("show_values", False),
    )


def build_bundle_message(address: str, values: tuple) -> bytes:
    builder = OscMessageBuilder(address=address)
    for v in values:
        builder.add_arg(float(v))
    return builder.build().dgram


def build_individual_messages(
    addresses: dict[str, str], values: tuple
) -> list[bytes]:
    messages = []
    for axis, value in zip(AXIS_NAMES, values):
        builder = OscMessageBuilder(address=addresses[axis])
        builder.add_arg(float(value))
        messages.append(builder.build().dgram)
    return messages


def run(cfg: Config) -> None:
    client = udp_client.SimpleUDPClient(cfg.target_host, cfg.target_port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((cfg.listen_host, cfg.listen_port))

    logging.info(
        "Listening on %s:%d → OSC %s:%d  (mode: %s)",
        cfg.listen_host, cfg.listen_port,
        cfg.target_host, cfg.target_port,
        cfg.mode,
    )

    try:
        while True:
            data, addr = sock.recvfrom(1024)

            if len(data) < OPENTRACK_SIZE:
                logging.warning(
                    "Short packet from %s (%d bytes, expected %d) — skipped",
                    addr, len(data), OPENTRACK_SIZE,
                )
                continue

            values = struct.unpack_from(OPENTRACK_FORMAT, data)

            if cfg.show_values:
                logging.debug(
                    "x=%.2f y=%.2f z=%.2f  yaw=%.2f pitch=%.2f roll=%.2f",
                    *values,
                )

            if cfg.mode == "bundle":
                dgram = build_bundle_message(cfg.bundle_address, values)
                client._sock.sendto(dgram, (cfg.target_host, cfg.target_port))
            else:
                for dgram in build_individual_messages(cfg.individual_addresses, values):
                    client._sock.sendto(dgram, (cfg.target_host, cfg.target_port))

    except KeyboardInterrupt:
        logging.info("Stopped.")
    finally:
        sock.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Forward OpenTrack UDP data as OSC messages."
    )
    parser.add_argument(
        "-c", "--config",
        default=Path(__file__).parent / "config.toml",
        type=Path,
        help="Path to config file (default: config.toml next to this script)",
    )
    args = parser.parse_args()

    if not args.config.exists():
        sys.exit(f"Config file not found: {args.config}")

    cfg = load_config(args.config)
    run(cfg)


if __name__ == "__main__":
    main()
