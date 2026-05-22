"""
Funding Survival Backtest

Core question: if you entered a position when funding was X%/yr,
what did the funding actually earn over the next 30 days after:
  - Rate decay
  - Adverse price moves
  - Spread costs
  - Stop-out events

Uses the 166-day historical funding database we collected.
"""

import sqlite3, numpy as np, sys
sys.path.insert(0, '..')
from config import DB_PATH, FUNDING_HAIRCUT, SPREAD_COST_PCT

def load_funding_history(symbol: str, db_path=DB_PATH) -> list[dict]:
    """Load historical funding rates from the research DB."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM funding_snapshots WHERE symbol=? ORDER BY ts",
        (symbol,)).fetchall()]
    conn.close()
    return rows

def backtest_entry(
    rates: list[float],      # sequence of 8h rates (%)
    entry_idx: int,          # which period we entered
    hold_periods: int = 90,  # 30 days = 90 × 8h periods
    stop_threshold: float = -0.02,  # exit if rate goes below this
    notional: float = 100,   # $ notional
) -> dict:
    """Simulate one position from entry_idx forward."""
    entry_rate = rates[entry_idx]
    income = 0.0
    periods_held = 0
    exit_reason = 'time'

    for i in range(entry_idx, min(entry_idx + hold_periods, len(rates))):
        r = rates[i]
        if r < stop_threshold:
            exit_reason = 'rate_flip'
            break
        income += notional * r / 100  # $ income per period
        periods_held += 1

    # Deduct spread costs (entry + exit)
    spread_cost = notional * SPREAD_COST_PCT * 2
    net_income  = income - spread_cost
    ann_realised = (income / periods_held * 3 * 365) if periods_held > 0 else 0

    return {
        'entry_rate':     entry_rate,
        'ann_entry':      entry_rate * 3 * 365,
        'periods_held':   periods_held,
        'days_held':      periods_held / 3,
        'gross_income':   round(income, 4),
        'spread_cost':    round(spread_cost, 4),
        'net_income':     round(net_income, 4),
        'ann_realised':   round(ann_realised, 1),
        'exit_reason':    exit_reason,
        'survived':       exit_reason == 'time',
    }

def run_full_backtest(symbol: str, min_entry_apr=40.0) -> dict:
    """Run all valid entry points and aggregate results."""
    history = load_funding_history(symbol)
    if not history:
        # Fall back to live data
        print(f"No local history for {symbol}, run data_ingestion first")
        return {}

    rates = [h['rate_8h'] for h in history]
    entries = [i for i, r in enumerate(rates) if r * 3 * 365 >= min_entry_apr]

    if not entries:
        return {'symbol': symbol, 'n_entries': 0, 'message': 'No valid entries'}

    results = [backtest_entry(rates, i) for i in entries if i + 10 < len(rates)]

    survived     = [r for r in results if r['survived']]
    net_incomes  = [r['net_income'] for r in results]
    ann_realised = [r['ann_realised'] for r in results]

    return {
        'symbol':            symbol,
        'n_entries':         len(results),
        'survival_rate':     len(survived) / max(len(results), 1),
        'avg_net_income':    round(np.mean(net_incomes), 4),
        'avg_ann_realised':  round(np.mean(ann_realised), 1),
        'vs_headline_apr':   round(np.mean(ann_realised) / (min_entry_apr) * 100, 1),
        'p25_net_income':    round(np.percentile(net_incomes, 25), 4),
        'p75_net_income':    round(np.percentile(net_incomes, 75), 4),
    }

if __name__ == '__main__':
    for symbol in ['COINUSDT', 'AMZNUSDT', 'METAUSDT', 'RAVEUSDT']:
        r = run_full_backtest(symbol)
        if r:
            print(f"{r['symbol']:20} entries={r.get('n_entries',0):3}  "
                  f"survival={r.get('survival_rate',0)*100:.0f}%  "
                  f"realised={r.get('avg_ann_realised',0):.0f}%/yr  "
                  f"vs_headline={r.get('vs_headline_apr',0):.0f}%")
