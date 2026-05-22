"""
Funding Survival Backtest

Core question: if you entered a position when funding was X%/yr,
what did the funding actually earn over the next 30 days after:
  - Rate decay
  - Adverse price moves
  - Spread costs
  - Stop-out events

Data: data/funding_history_166d.csv (46,511 rows, 8h intervals)
Format: symbol, timestamp (ISO), fundingRate (decimal, e.g. 0.0006 = 0.06%/8h)
"""

import csv, numpy as np, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import FUNDING_HAIRCUT, SPREAD_COST_PCT, ENTER_FUNDING_APR, MIN_FUNDING_APR

DATA_FILE = Path(__file__).parent.parent / "data" / "funding_history_166d.csv"


def load_rates(symbol: str) -> list[float]:
    """Load 8h funding rates for a symbol (as % per period, not decimal)."""
    rates = []
    with open(DATA_FILE) as f:
        for row in csv.DictReader(f):
            if row['symbol'] == symbol:
                rates.append(float(row['fundingRate']) * 100)  # to %
    return rates


def available_symbols() -> list[str]:
    """List all symbols in the dataset."""
    seen = set()
    with open(DATA_FILE) as f:
        for row in csv.DictReader(f):
            seen.add(row['symbol'])
    return sorted(seen)


def backtest_entry(
    rates: list[float],
    entry_idx: int,
    hold_periods: int = 90,      # 30 days = 90 × 8h
    stop_threshold: float = -0.005,  # exit if rate < -0.005%/8h
    notional: float = 100.0,
) -> dict:
    """Simulate one position from entry_idx forward."""
    if entry_idx >= len(rates):
        return {}
    entry_rate = rates[entry_idx]
    income = 0.0
    periods_held = 0
    exit_reason = 'time'

    for i in range(entry_idx, min(entry_idx + hold_periods, len(rates))):
        r = rates[i]
        if r < stop_threshold:
            exit_reason = 'rate_flip'
            break
        income += notional * r / 100
        periods_held += 1

    spread_cost = notional * SPREAD_COST_PCT * 2
    net_income  = income - spread_cost
    ann_realised = (income / max(periods_held, 1) * 3 * 365) if periods_held > 0 else 0

    return {
        'entry_rate':    round(entry_rate, 6),
        'ann_entry':     round(entry_rate * 3 * 365, 1),
        'periods_held':  periods_held,
        'days_held':     round(periods_held / 3, 1),
        'gross_income':  round(income, 4),
        'spread_cost':   round(spread_cost, 4),
        'net_income':    round(net_income, 4),
        'ann_realised':  round(ann_realised, 1),
        'exit_reason':   exit_reason,
        'survived':      exit_reason == 'time',
    }


def run_backtest(symbol: str, min_entry_apr: float = ENTER_FUNDING_APR) -> dict:
    """Run all valid entry points for a symbol and aggregate."""
    rates = load_rates(symbol)
    if not rates:
        return {'symbol': symbol, 'n_entries': 0, 'error': 'no data'}

    min_rate_per_period = min_entry_apr / 3 / 365
    entries = [i for i, r in enumerate(rates)
               if r >= min_rate_per_period and i + 10 < len(rates)]

    if not entries:
        return {'symbol': symbol, 'n_entries': 0, 'n_total_periods': len(rates)}

    results = [backtest_entry(rates, i) for i in entries]
    results = [r for r in results if r]

    survived     = [r for r in results if r.get('survived')]
    net_incomes  = [r['net_income'] for r in results]
    ann_realised = [r['ann_realised'] for r in results]

    return {
        'symbol':           symbol,
        'n_periods':        len(rates),
        'n_entries':        len(results),
        'survival_rate':    round(len(survived) / max(len(results), 1), 3),
        'avg_net_income':   round(float(np.mean(net_incomes)), 4),
        'avg_ann_realised': round(float(np.mean(ann_realised)), 1),
        'headline_apr':     round(min_entry_apr, 1),
        'realised_pct_of_headline': round(
            float(np.mean(ann_realised)) / min_entry_apr * 100, 1),
        'p25_net':          round(float(np.percentile(net_incomes, 25)), 4),
        'p75_net':          round(float(np.percentile(net_incomes, 75)), 4),
        'flip_count':       len(results) - len(survived),
    }


def run_all(symbols: list[str] | None = None, min_apr: float = ENTER_FUNDING_APR) -> list[dict]:
    if symbols is None:
        symbols = available_symbols()
    return [run_backtest(s, min_apr) for s in symbols]


if __name__ == '__main__':
    targets = ['COINUSDT', 'AMZNUSDT', 'METAUSDT', 'RAVEUSDT',
               'JELLYJELLYUSDT', 'BASUSDT', 'BTCUSDT', 'ETHUSDT']
    print(f"\n{'Symbol':22} {'Entries':>8} {'Survival':>9} {'Realised%/yr':>13} {'vs headline':>12} {'Flip':>5}")
    print('─' * 75)
    for sym in targets:
        r = run_backtest(sym)
        if r.get('n_entries', 0) == 0:
            print(f"  {sym:20}  no entries above threshold"); continue
        icon = '✅' if r['survival_rate'] > 0.7 else ('⚠️' if r['survival_rate'] > 0.4 else '❌')
        print(f"  {icon} {sym:20} {r['n_entries']:>7}  "
              f"{r['survival_rate']*100:>8.0f}%  "
              f"{r['avg_ann_realised']:>12.1f}%  "
              f"{r['realised_pct_of_headline']:>11.0f}%  "
              f"{r['flip_count']:>4}")
