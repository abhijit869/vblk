"""Command line interface for the JARVIS v0.1 prototype."""

from __future__ import annotations

import argparse
import json
import sys

from jarvis_core.config import build_ai_gateway, load_ai_config
from jarvis_core.core import JarvisCore
from jarvis_core.memory import SQLiteMemoryEngine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the JARVIS v0.1 control loop")
    parser.add_argument(
        "request", nargs="+", help="Natural-language request or 'daemon'"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full structured response and audit trail",
    )
    args = parser.parse_args(argv)

    try:
        config = load_ai_config()
    except ValueError as exc:
        print(f"jarvis: configuration error: {exc}", file=sys.stderr)
        return 2

    core = JarvisCore(ai_gateway=build_ai_gateway(config), memory_engine=SQLiteMemoryEngine())

    if args.request[0] == "daemon":
        from jarvis_core.dbus_service import start_dbus_service

        try:
            start_dbus_service(core)
            # Run forever
            import time

            while True:
                time.sleep(1)
        except Exception as e:
            print(f"Daemon Error: {e}", file=sys.stderr)
            return 1

    response = core.handle_text(" ".join(args.request))

    if args.json:
        print(json.dumps(response, indent=2, default=str))
        return 0

    print(response["answer"])
    ai = response["ai"]
    if ai.get("fallback_from"):
        print(
            f"\n[{ai['fallback_from']} unavailable ({ai.get('error')}); answered by {ai['provider']}]",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
