"""`ctr`: command-line interface of the strategy and data-analysis system.

  ctr run DATA.csv [--asset btc|eth] [--start D] [--end D] [--out DIR]   analyse + backtest + next decision
  ctr check DATA.csv                                                    data-quality checks only
  ctr download --asset btc --start D --end D [--out DIR] [--run]        fetch Binance hourly candles
  ctr reproduce [--asset btc|eth|all]                                   rebuild the competition results
  ctr selftest                                                          lookahead, engine and frozen-result tests
  ctr info                                                              strategies, costs, versions, bundled data
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from src.system.strategies import STRATEGIES, get, guess_asset

ROOT = Path(__file__).resolve().parents[2]
VERSION = "1.0.0"
_TTY = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _TTY else s


def bold(s): return _c("1", s)
def dim(s): return _c("2", s)
def green(s): return _c("32", s)
def red(s): return _c("31", s)
def yellow(s): return _c("33", s)
def cyan(s): return _c("36", s)


def banner(sub: str):
    line = "─" * 64
    print(cyan(line))
    print(f"{bold(cyan('  CTR'))}  {bold('Calm-Trend Regime')} · strategy & data-analysis system  {dim('v' + VERSION)}")
    print(f"  {dim(sub)}")
    print(cyan(line), flush=True)


def step(msg: str):
    print(f"  {cyan('▸')} {msg}", flush=True)


def kv(rows: list[tuple[str, str]], width: int = 30):
    for k, v in rows:
        print(f"    {dim(k.ljust(width))} {v}")


def _signed(v: float, fmt: str = "{:+,.2f}") -> str:
    s = fmt.format(v)
    return green(s) if v > 0 else red(s) if v < 0 else s


def _asset(args) -> str:
    asset = args.asset or guess_asset(args.data)
    if asset is None:
        sys.exit(red(f"  cannot tell the asset from '{args.data}': pass --asset btc or --asset eth"))
    return asset


# ---------------------------------------------------------------- commands
def cmd_run(args) -> int:
    from src.system.pipeline import run
    asset = _asset(args)
    strategy = get(asset)
    banner(f"run · {strategy.symbol} · {strategy.name}")
    t = time.time()
    res = run(args.data, asset, args.start, args.end, args.out, verify=not args.no_verify, log=step)
    m, d, q = res["metrics"], res["decision"], res["quality"]
    print()
    for n in res["notes"]:
        print(f"  {yellow('!')} {n}")
    print(bold("  Data"))
    kv([("bars / days", f"{q['bars']:,} ({q['input_bar']}) / {q['days']:,}"),
        ("filled gaps / outage bars", f"{q['missing_bars_filled']} / {q['empty_outage_bars']}"),
        ("realised measures", q["realised_measures"])])
    print(bold(f"\n  Strategy  {res['start']} → {res['end']}"))
    kv([("total return", _signed(m["Total Return (%)"], "{:+,.1f}%") + dim(f"   buy & hold {m['Buy-and-Hold Return (%)']:+,.1f}%")),
        ("Sharpe / Sortino", f"{m['Sharpe Ratio']:.2f} / {m['Sortino Ratio']:.2f}" + dim(f"   buy & hold Sharpe {m['Buy-and-Hold Sharpe Ratio']:.2f}")),
        ("max drawdown", red(f"{m['Max Drawdown (%)']:.1f}%") + dim(f"   buy & hold {m['Buy-and-Hold Max Drawdown (%)']:.1f}%")),
        ("closed trades (short)", f"{m['Total Closed Trades']} ({m['Short Trades']})   win rate {m['Win Rate (%)']:.1f}%"),
        ("net profit", _signed(m["Net Profit (USDT)"], "{:+,.0f} USDT")),
        ("quarters beating B&H", f"{m['Quarters Beating Buy-and-Hold (%)']:.0f}%"),
        ("Sharpe at 2x costs", f"{m['Sharpe at 2x costs']:.2f}")])
    print(bold("\n  Market"))
    for line in res["reading"]:
        print(f"    {dim('·')} {line}")
    side = d["side"]
    colour = green if side == "LONG" else red if side == "SHORT" else yellow
    print(bold("\n  Next decision"))
    kv([("at the close of", d["decided_at_close_of"]), ("market state", d["market_state"]),
        ("position from next open", colour(f"{side} {abs(d['target_position_x_equity']):.2f}× equity"))])
    print(f"\n  {green('✓')} report: {bold(str(res['out'] / 'report.md'))}  {dim(f'({time.time() - t:.0f}s)')}\n")
    return 0


def cmd_check(args) -> int:
    from src.system.ingest import load_dataset
    banner(f"check · {args.data}")
    ds = load_dataset(args.data, (args.asset or guess_asset(args.data) or "unknown").upper())
    kv([(k.replace("_", " "), str(v)) for k, v in ds.quality.items()])
    f = ds.daily
    kv([("price range", f"{f['close'].min():,.2f} → {f['close'].max():,.2f}"),
        ("first / last close", f"{f['close'].iloc[0]:,.2f} / {f['close'].iloc[-1]:,.2f}")])
    print(f"\n  {green('✓')} data is usable\n")
    return 0


def cmd_download(args) -> int:
    from src.system.download import download_to
    strategy = get(args.asset)
    banner(f"download · {strategy.symbol} · {args.start} → {args.end}")
    path = download_to(strategy.symbol, args.start, args.end, args.out, log=step)
    print(f"\n  {green('✓')} saved {bold(str(path))}\n")
    if args.run:
        return cmd_run(argparse.Namespace(data=str(path), asset=args.asset, start=None, end=None, out=None, no_verify=False))
    return 0


def cmd_reproduce(args) -> int:
    banner("reproduce · competition backtests 2021-2024, 2025, 2021-2025")
    targets = ["btc", "eth"] if args.asset == "all" else [args.asset]
    for key in targets:
        step(f"{STRATEGIES[key].symbol}: {STRATEGIES[key].name} → results/{key}/")
        module = "scripts.run_btc_strategy" if key == "btc" else "scripts.run_eth_strategy"
        code = subprocess.call([sys.executable, "-m", module], cwd=ROOT)
        if code:
            return code
    print(f"\n  {green('✓')} results written to {bold('results/')}\n")
    return 0


def cmd_selftest(args) -> int:
    banner("selftest · lookahead, engine, metrics and frozen results")
    return subprocess.call([sys.executable, "-m", "pytest", "-q", "tests"] + args.pytest_args, cwd=ROOT)


def cmd_info(args) -> int:
    from src.system.pipeline import _git_commit, _versions
    banner("info")
    print(bold("  Strategies (frozen)"))
    for k, s in STRATEGIES.items():
        c = s.config()
        kv([(f"{k}  {s.symbol}", s.name),
            ("", dim(f"max {c.max_position}x long" + (", 0.5x short" if c.allow_short else ", long only")
                     + f", {100 * c.cost_rate:.2f}% per fill, USDT borrow {100 * c.borrow_rate:.0f}%/yr"
                     + (f", coin borrow {100 * c.short_borrow_rate:.0f}%/yr" if c.allow_short else "")))])
    print(bold("\n  Bundled data"))
    for f in sorted((ROOT / "data" / "raw").glob("*.csv")):
        kv([(f.name, f"{f.stat().st_size / 1e6:.1f} MB")])
    print(bold("\n  Environment"))
    kv([(k, v) for k, v in _versions().items()] + [("git commit", _git_commit() or "n/a")])
    print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ctr", description="Calm-Trend Regime: run the frozen BTC/ETH strategies and the "
                                "data analysis on any candle data.", formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__.split("\n", 2)[2])
    p.add_argument("--version", action="version", version=f"ctr {VERSION}")
    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    r = sub.add_parser("run", help="analyse a dataset and run the frozen strategy on it")
    r.add_argument("data", help="candle CSV (hourly or daily; Binance kline format or any time+OHLC table)")
    r.add_argument("--asset", choices=sorted(STRATEGIES), help="btc or eth (default: from the file name)")
    r.add_argument("--start", help="first day to evaluate (earlier rows are warm-up); default: first day")
    r.add_argument("--end", help="last day to evaluate; default: last day")
    r.add_argument("--out", help="output folder (default: runs/<asset>_<file>_<time>/)")
    r.add_argument("--no-verify", action="store_true", help="skip the causality check (faster)")
    r.set_defaults(func=cmd_run)

    c = sub.add_parser("check", help="clean a dataset and print its quality report")
    c.add_argument("data")
    c.add_argument("--asset", choices=sorted(STRATEGIES))
    c.set_defaults(func=cmd_check)

    d = sub.add_parser("download", help="download hourly candles from Binance's public API")
    d.add_argument("--asset", choices=sorted(STRATEGIES), required=True)
    d.add_argument("--start", required=True, help="e.g. 2026-01-01")
    d.add_argument("--end", required=True, help="e.g. 2026-10-01")
    d.add_argument("--out", default=str(ROOT / "data" / "external"), help="folder (default: data/external)")
    d.add_argument("--run", action="store_true", help="run the system on the downloaded file")
    d.set_defaults(func=cmd_download)

    rp = sub.add_parser("reproduce", help="rebuild the competition results in results/")
    rp.add_argument("--asset", choices=sorted(STRATEGIES) + ["all"], default="all")
    rp.set_defaults(func=cmd_reproduce)

    t = sub.add_parser("selftest", help="run the test suite (lookahead, engine, frozen results)")
    t.add_argument("pytest_args", nargs=argparse.REMAINDER)
    t.set_defaults(func=cmd_selftest)

    i = sub.add_parser("info", help="show strategies, costs, versions and bundled data")
    i.set_defaults(func=cmd_info)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as e:
        print(red(f"\n  ✗ {e}\n"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
