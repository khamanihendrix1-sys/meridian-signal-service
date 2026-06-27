from __future__ import annotations

import argparse

from meridian.observability.logging import logger


def main() -> None:
    """Command-line entrypoint for service utilities."""
    parser = argparse.ArgumentParser(description="Meridian CLI")
    parser.add_argument("command", choices=["seed-mock"], help="CLI command to execute")
    args = parser.parse_args()

    if args.command == "seed-mock":
        logger.info("seed-mock called")
        print("This command is a placeholder until seed implementation is added.")
