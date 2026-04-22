import argparse
import json
import os
import time

from lambda_function import run_temperature_monitor


try:
    DEFAULT_INTERVAL_MINUTES = int(os.getenv("MONITOR_INTERVAL_MINUTES", "15"))
except ValueError:
    DEFAULT_INTERVAL_MINUTES = 15


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa o monitor de temperatura localmente."
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Mantem o monitor rodando continuamente.",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=DEFAULT_INTERVAL_MINUTES,
        help="Intervalo entre verificacoes quando usado com --loop.",
    )
    return parser.parse_args()


def run_once() -> dict:
    return run_temperature_monitor({"action": "monitor_temperature"})


def main() -> None:
    args = parse_args()

    while True:
        result = run_once()
        print(json.dumps(result, indent=2, ensure_ascii=True))

        if not args.loop:
            return

        sleep_seconds = max(args.interval_minutes, 1) * 60
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
