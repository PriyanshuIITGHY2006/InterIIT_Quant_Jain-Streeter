# Backtest Engine: Research & Design

Code: `src/backtest/` · Tests: `tests/` (`.venv/bin/python -m pytest -q`) · Demo: `.venv/bin/python -m scripts.run_engine_demo`

The engine's one job is to answer honestly: *what would this strategy have earned, trading only on information it had at the time, after paying 0.15% on every fill?* Every design choice below favours **correctness and pessimism over speed and convenience**. An optimistic backtest is worse than none.

---

## 1. Research decisions

### 1.1 Architecture: event-driven bar loop
| Option | Pros | Cons |
|---|---|---|
| Vectorised (shift positions, multiply by returns) | Very fast | Stops, trailing stops, gap fills, per-trade fees and trade logs are awkward and easy to get subtly wrong; look-ahead hides in a single misplaced `shift` |
| **Event-driven bar loop** ✅ | Each bar is processed in the order a trader lives it (open → intrabar → close → decide); exact trade-level accounting; easy to read and to audit | Slower |
| Hybrid (vectorised signals + loop execution) ✅ | Signals computed once with pandas; execution done in the loop | Needs a separate check that the signals themselves are causal |

**Decision:** strategies compute their signals with vectorised pandas code, and the engine executes them in a plain Python bar loop. ~26k hourly bars run in well under a second, so speed isn't a concern. The risk that a vectorised signal peeks ahead is handled by an automatic truncation check (§1.9).

### 1.2 Strategy–engine interface: target positions, lagged by the engine
The strategy returns one row per bar: `target` ∈ [−1, 1] (fraction of equity; 0 = flat) plus optional `stop_dist`, `tp_dist`, `trail_dist` (price distances). Row *i* may use data up to bar *i*'s close. **The engine, not the strategy, applies the one-bar lag:** row *i* is executed at bar *i+1*'s open. A strategy therefore cannot trade on the bar it just observed, even by mistake. Signals must share the data's exact index, otherwise the engine raises an error, so misaligned signals can't slip through. `backtest(data, signal_fn)` first runs the causality check and then the engine, making look-ahead loud rather than silent.

*Alternative considered:* calling the strategy bar by bar with a growing data slice. It's structurally causal but O(n²) with pandas indicators (minutes per run). The truncation check gives the same guarantee at a fraction of the cost.

### 1.3 Orders and fills
| Event | Fill rule | Why |
|---|---|---|
| Signal entry / exit / reversal | Next tradable bar's **open** | The earliest price actually available after the decision |
| Stop-loss / trailing stop | At the stop level if touched inside the bar; **at the open if the bar opens beyond it** (gap) | Our data has real gaps and 10–20% liquidation wicks |
| Take-profit | At the target if touched; at the open if the bar opens beyond it | A resting limit order fills at the better open |
| Stop and target both touched in one bar | **Stop assumed first** | OHLC can't tell which came first, so assume the worst |
| Trailing stop level | Uses the best price up to the **previous** bar | Using the same bar's high to trail and then stop out would assume the high came before the low |
| Time exit (`max_holding_bars`) | Decided at the close, executed at the next open | Same timing rule as signals |
| Reversal (long → short) | Close, then open, at the same open, with **both** fees | Two transactions |
| End of data | Closed at the last close, with a fee | Every trade in the log is closed and costed |

After a stop, take-profit, trailing or time exit, the engine **does not re-enter the same side until the signal changes** (configurable), so a stop can't be immediately undone by a still-long signal.

### 1.4 Costs and slippage
A flat **0.15% of notional on every fill** (`cost_rate=0.0015`), as the problem statement requires; a round trip costs 0.30%. Sizing reserves room for the entry fee (`qty = fraction × equity / (price × (1 + cost))`), so a fully invested long never runs cash negative. Optional extra slippage (e.g. wider fills in high-range bars) was considered for stress tests but **not built**, to keep the engine simple. Raising `cost_rate` gives a simple stress test.

### 1.5 Position sizing and accounting
- Cash-based accounting. Long: `cash −= qty·price + fee` on entry, `cash += qty·price − fee` on exit. Short: the mirror image.
- `equity = cash + signed_qty × close` at every bar.
- Size is set **at entry**, from equity at the moment of the fill (the book is flat, so equity = cash, a value known then). Changing |target| without changing side doesn't resize. This keeps one clean trade per position and avoids hidden partial fills.
- No leverage: `max_position` defaults to 1.0. Shorts are **off by default** (`allow_short=False`) and raise an error if requested.
- If equity reaches ≤ 0 the engine halts trading. A `max_drawdown_halt` and an `exposure_cap(time, equity, peak)` hook exist for global risk rules.

### 1.6 Equity marking
Equity is marked to market at every bar's close (realised cash plus unrealised position value). Drawdowns, Sharpe and Sortino all use this curve, so open-trade losses count; they aren't hidden until the exit.

### 1.7 Metric definitions
| Metric | Formula |
|---|---|
| Trade PnL | **Net** of both fees: `side·qty·(exit − entry) − entry_fee − exit_fee` |
| Gross Profit / Gross Loss | Σ net PnL of winning / losing trades (winner: net PnL > 0) |
| Net Profit | Final equity − initial capital (= Gross Profit + Gross Loss; tested) |
| Win Rate | winners / closed trades × 100 |
| Max Drawdown | min over bars of `equity / running_max(equity) − 1`, in % |
| Avg / Largest Win & Loss | Mean / max / min of net PnL over winners or losers (USDT) |
| Buy-and-Hold Return | Buy at the first tradable open after bar 0, sell at the last close, same 0.15% costs |
| Sharpe | `mean(r) / std(r) × √365`, where r = **daily** returns of equity (last value per UTC day), risk-free rate 0 |
| Sortino | `mean(r) / √mean(min(r,0)²) × √365` on the same daily returns |
| Holding Duration | `exit_time − entry_time` (average and maximum) |
| Extras | Total and annualised return (CAGR), Calmar, exposure %, long/short counts, total fees, recovery time of the max drawdown, longest time under water, % quarters beating buy-and-hold, benchmark drawdown and Sharpe, deferred orders |

**Why daily returns for Sharpe/Sortino:** the same definition works for 1h, 4h and 1d strategies, so results are comparable. It avoids intraday microstructure noise, and it's the most common convention, so judges will expect it. Crypto trades every day, hence √365.

### 1.8 Benchmark
Buy-and-hold enters at the **same earliest moment a strategy could** (the first tradable open after the first bar) and pays the same costs. A strategy that is always long reproduces it exactly (tested). The quarterly table compares the strategy's return with the asset's price return for each calendar quarter (partial first and last quarters included).

### 1.9 How the engine is validated
| Check | What it proves |
|---|---|
| Next-bar execution test | The lag can't be bypassed |
| Hand-computed round trip (967.05 USDT) | Costs and PnL are exact, long and short |
| Gap, same-bar and trailing tests | Fills are pessimistic |
| Outage tests | No fills or stops on outage bars; orders deferred |
| Invariants on real BTC data | equity = cash + position value on every bar; Σ trade PnL = equity change; fees are never double-counted |
| **Truncation test** | Running up to *T* reproduces the full run's history up to *T* exactly |
| **Causality check with a cheating strategy** | A signal using `shift(-1)` is caught |
| Always-flat / always-long | No phantom PnL; always-long = benchmark exactly |
| Random signals on zero-drift prices | Fees are exactly 0.30% per round trip and the price-move part averages zero (no hidden edge or leak) |

### 1.10 Common backtest bugs and how the design prevents them
| Bug | Prevention |
|---|---|
| Trading on the bar's own close (look-ahead) | The engine applies the lag itself; tested |
| Signals computed with future data | `check_signals_causal` truncation check, run automatically by `backtest()` |
| Off-by-one alignment | Signals must share the data's exact index; next-open test |
| Optimistic stops (fill at stop despite a gap; target before stop) | Gap → open; stop first; trailing uses the previous bar only |
| Double-counted or missing fees | Fee on every fill, fills log reconciled with trades in tests |
| Trading during outages | `is_filled` / `trades == 0` bars are skipped |
| Resampling leakage | Bars are labelled by open time; resampled bars are usable only after they close (project rule in `CLAUDE.md`) |
| Survivorship bias | Not applicable: two fixed, listed pairs |
| Tuning on the test split | Engine is split-agnostic; the demo uses train only |

---

## 2. API

```python
from src.backtest import BacktestConfig, backtest, run_backtest, compute_metrics, save_report
from src.data.loader import load_market

data = load_market("BTCUSDT", "1h", "train")

def my_signal(data):                       # uses data up to each bar's close only
    return pd.DataFrame({"target": ..., "stop_dist": ...}, index=data.index)

config = BacktestConfig(initial_capital=10_000, cost_rate=0.0015, allow_short=False,
                        max_holding_bars=None, max_drawdown_halt=None)
result = backtest(data, my_signal, config)          # causality check + run
metrics = compute_metrics(result, data)             # the 15 required metrics + extras
save_report(result, data, metrics, "results/btc/my_run", "BTC my strategy")
```

`BacktestResult` holds: `equity`, `cash`, `position` (per bar), `trades` (entry/exit time and price, side, qty, gross PnL, fees, net PnL, return %, bars held, duration, exit reason, MAE %, MFE %), `fills`, `deferred`, `config`.

`save_report` writes `metrics.csv`, `metrics.md`, `trades.csv`, `fills.csv`, `equity.csv`, `quarterly.csv`, `equity.png` (equity and drawdown vs buy-and-hold) and `trades.png`.

---

## 3. Known limitations
- **MAE/MFE** include the full high/low of the exit bar, even the part after a stop filled, so MAE is slightly pessimistic.
- **Intrabar exit times** are recorded as the bar's open timestamp, so durations have one-bar resolution.
- **No partial resizing** of an open position; strategies that scale in or out need a new feature.
- **One market per run.** Portfolio-level effects (BTC and ETH crashing together) must be combined outside the engine.

## 4. Open questions for the team
1. **Is shorting allowed?** The problem statement is silent and the data is spot. Default: off.
2. **Is leverage allowed?** Default: none (`max_position = 1`).
3. **Sharpe/Sortino on daily returns?** This is our choice; confirm it matches what the organisers compute.
4. **"Gross Profit" definition:** we use winning trades' PnL *net* of fees. If the organisers mean before fees, it's a one-line change (use `gross_pnl`).
5. **Starting capital:** 10,000 USDT by default; the problem statement doesn't specify.
6. **Buy-and-hold** is reported with costs. Should the report also show the no-cost price return?
