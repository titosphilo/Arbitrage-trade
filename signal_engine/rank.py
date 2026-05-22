"""
Funding opportunity ranker.

Scores each perp on five dimensions:
  1. APR score       — headline funding rate, normalised
  2. Persistence     — historical stability of positive rate
  3. Liquidity       — OI and volume filters
  4. Crowding        — long/short ratio (extreme = crowded, risky)
  5. Flip risk       — probability rate goes negative next period

Final score 0-100. Only trade > 60.
"""

import numpy as np
from dataclasses import dataclass
from config import MIN_FUNDING_APR, ENTER_FUNDING_APR, MIN_OI_USD, MIN_VOLUME_USD

@dataclass
class Signal:
    symbol:       str
    ann_pct:      float
    persistence:  float   # 0-1: fraction of periods positive (last 30 days)
    volume_usd:   float
    oi_usd:       float
    ls_ratio:     float   # long/short ratio  >1 = more longs
    flip_risk:    float   # 0-1: probability rate flips negative
    score:        float   # 0-100 composite
    action:       str     # ENTER / HOLD / WATCH / EXIT / SKIP


def compute_score(
    ann_pct:      float,
    persistence:  float,
    volume_usd:   float,
    oi_usd:       float,
    ls_ratio:     float,
    flip_risk:    float,
) -> float:
    """Composite score 0-100."""
    # 1. APR component (40 pts max)
    apr_score = min(ann_pct / 200 * 40, 40)

    # 2. Persistence (25 pts max)
    persistence_score = persistence * 25

    # 3. Liquidity (15 pts max)
    liq_ok = volume_usd > MIN_VOLUME_USD and oi_usd > MIN_OI_USD
    liq_score = 15 if liq_ok else 5 if (volume_usd > MIN_VOLUME_USD * 0.5) else 0

    # 4. Crowding (10 pts) — moderate crowding is good (we earn funding)
    #    but extreme crowding (ls_ratio > 3) = squeeze risk → penalty
    if ls_ratio < 1.2:
        crowd_score = 2   # barely crowded, less funding likely
    elif ls_ratio < 2.5:
        crowd_score = 10  # sweet spot
    else:
        crowd_score = 4   # dangerously crowded, squeeze risk

    # 5. Flip risk penalty (10 pts max deduction)
    flip_penalty = flip_risk * 10

    return round(apr_score + persistence_score + liq_score + crowd_score - flip_penalty, 1)


def classify(score: float, ann_pct: float) -> str:
    if ann_pct < 0:              return 'EXIT'
    if ann_pct < MIN_FUNDING_APR: return 'EXIT'
    if score < 30:               return 'SKIP'
    if score < 50:               return 'WATCH'
    if score < 65:               return 'HOLD'
    return 'ENTER'


def estimate_flip_risk(rate_history: list[float]) -> float:
    """Simple flip risk: fraction of sign changes in recent history."""
    if len(rate_history) < 3:
        return 0.3  # unknown → moderate risk
    signs = [1 if r > 0 else -1 for r in rate_history]
    flips = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i-1])
    return min(flips / len(signs), 1.0)


def rank_opportunities(candidates: list[dict]) -> list[Signal]:
    """
    candidates: list of dicts with keys:
        symbol, ann_pct, persistence, volume_usd, oi_usd, ls_ratio, rate_history
    """
    signals = []
    for c in candidates:
        flip_risk = estimate_flip_risk(c.get('rate_history', []))
        score = compute_score(
            ann_pct=c['ann_pct'],
            persistence=c.get('persistence', 0.7),
            volume_usd=c.get('volume_usd', 0),
            oi_usd=c.get('oi_usd', 0) * c.get('mark_px', 0),
            ls_ratio=c.get('ls_ratio', 1.5),
            flip_risk=flip_risk,
        )
        signals.append(Signal(
            symbol=c['symbol'], ann_pct=c['ann_pct'],
            persistence=c.get('persistence', 0),
            volume_usd=c.get('volume_usd', 0),
            oi_usd=c.get('oi_usd', 0),
            ls_ratio=c.get('ls_ratio', 1.5),
            flip_risk=flip_risk, score=score,
            action=classify(score, c['ann_pct']),
        ))
    return sorted(signals, key=lambda s: -s.score)
