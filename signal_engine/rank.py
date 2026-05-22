"""Rank perps by funding APR and composite edge score."""
import numpy as np
from dataclasses import dataclass, field
from config import MIN_FUNDING_APR, ENTER_FUNDING_APR, STRONG_APR

@dataclass
class Signal:
    symbol:            str
    funding_ann:       float        # annualised funding %
    basis_ann:         float = 0.0
    persistence_score: float = 0.0
    liquidity_score:   float = 0.0
    crowding_score:    float = 0.0
    flip_risk:         float = 0.0
    edge_score:        float = 0.0
    status:            str   = "NEUTRAL"

    def classify(self) -> "Signal":
        if   self.funding_ann >= STRONG_APR:       self.status = "ENTER"
        elif self.funding_ann >= ENTER_FUNDING_APR: self.status = "ENTER"
        elif self.funding_ann >= MIN_FUNDING_APR:   self.status = "HOLD"
        elif self.funding_ann > 0:                  self.status = "WATCH"
        else:                                       self.status = "EXIT"
        return self


def compute_edge_score(s: Signal) -> float:
    apr_score  = min(s.funding_ann / 2, 50)
    pers_score = s.persistence_score * 0.25
    liq_score  = s.liquidity_score   * 0.15
    flip_pen   = s.flip_risk         * 0.10
    return max(0, apr_score + pers_score + liq_score - flip_pen)


def rank_by_apr(signals: list) -> list:
    return sorted(signals, key=lambda s: -s.funding_ann)


def from_funding_records(records: list) -> list:
    signals = []
    for r in records:
        ann = float(r.get("funding_rate", 0)) * 100 * 3 * 365
        s = Signal(symbol=r["symbol"], funding_ann=ann)
        s.edge_score = compute_edge_score(s)
        s.classify()
        signals.append(s)
    return rank_by_apr(signals)


def estimate_flip_risk(rate_history: list[float]) -> float:
    """Fraction of sign changes in recent rate history."""
    if len(rate_history) < 3:
        return 0.3
    signs = [1 if r > 0 else -1 for r in rate_history]
    flips = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i-1])
    return min(flips / len(signs), 1.0)
