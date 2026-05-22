"""
Funding Survival Test: Track 1

Research question:
  Does headline APR survive for 7+ days after entry?

Method:
  1. For each coin, take the funding rate at entry
  2. Track rate evolution over next 7/14/30 days
  3. Compute: what % of APR was collected before rate decayed below exit threshold?
  4. Compare to price move (MTM PnL)

Output:
  Survival rate table by entry APR tier
"""
import numpy as np
import sqlite3
from config import DB_PATH


def load_funding_history(symbol: str, limit=100) -> list[float]:
    conn = sqlite3.connect(DB_PATH)
    rates = [r[0] for r in conn.execute(
        "SELECT funding_rate FROM funding_snapshots WHERE symbol=? ORDER BY ts DESC LIMIT ?",
        (symbol, limit)).fetchall()]
    conn.close()
    return list(reversed(rates))


def survival_by_tier(histories: dict[str, list[float]],
                     tiers=[(0.03, 0.10), (0.10, 0.30), (0.30, np.inf)]) -> dict:
    """
    Group coins by entry funding rate tier and measure survival.
    tiers: list of (min_rate, max_rate) in %/8h
    """
    results = {}
    for label, (lo, hi) in zip(["Moderate (10-40%)", "High (40-100%)", "Extreme (100%+)"], tiers):
        matching = {sym: hist for sym, hist in histories.items()
                    if hist and lo <= hist[0]*100 < (hi if hi != np.inf else 9999)}
        
        if not matching:
            results[label] = {"n": 0}
            continue
        
        survival_rates = []
        for sym, hist in matching.items():
            entry_rate = hist[0] * 100
            exit_idx = next((i for i, r in enumerate(hist) if r * 100 < 0.01), len(hist))
            collected = sum(r * 100 for r in hist[:exit_idx])
            max_possible = entry_rate * len(hist)
            survival_rates.append(collected / max_possible if max_possible > 0 else 0)
        
        results[label] = {
            "n": len(matching),
            "avg_survival": np.mean(survival_rates) * 100,
            "median_survival": np.median(survival_rates) * 100,
            "symbols": list(matching.keys()),
        }
    
    return results
