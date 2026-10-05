"""Simplest way to use the system (same as the `ctr` command).

  python run.py DATA.csv                 analyse DATA.csv and run the frozen strategy (asset from the file name)
  python run.py DATA.csv eth             the same, asset given explicitly
  python run.py download btc 2026-01-01 2026-10-01     fetch Binance hourly candles, then run on them
  python run.py reproduce                rebuild the competition results in results/
  python run.py selftest                 run the test suite
Everything else: python run.py --help
"""
import sys

from src.system.cli import main

COMMANDS = {"run", "check", "download", "reproduce", "selftest", "info", "-h", "--help", "--version"}


def translate(argv: list[str]) -> list[str]:
    if not argv:
        print(__doc__)
        sys.exit(0)
    if argv[0] == "download" and len(argv) == 4 and not argv[1].startswith("-"):
        return ["download", "--asset", argv[1], "--start", argv[2], "--end", argv[3], "--run"]
    if argv[0] in COMMANDS:
        return argv
    if len(argv) >= 2 and argv[1] in ("btc", "eth"):
        return ["run", argv[0], "--asset", argv[1], *argv[2:]]
    return ["run", *argv]


if __name__ == "__main__":
    sys.exit(main(translate(sys.argv[1:])))
