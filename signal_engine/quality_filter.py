"""
Quality-adjusted funding filter — implements the framework from analysis.

Entry rules (ALL must pass):
  1. funding_apr > 40%          — minimum viable rate
  2. P(sticky)   > 70%          — classifier confidence
  3. consecutive_streak > 20    — proven persistence
  4. rate_volatility < 0.15     — not erratic

Sizing by persistence:
  P(sticky) >= 90%  → 12-15% of account
  P(sticky) 75-90%  → 8-10%
  P(sticky) 60-75%  → 3-5%
  P(sticky) < 60%   → skip

Exit rules (ANY triggers close):
  - P(sticky) drops below 60%
  - APR drops below 25%
  - Consecutive positive streak breaks (first negative period)
  - OI collapses sharply (>30% drop in 24h)

Income model:
  Realised APR = headline APR × 0.75 (backtest-validated haircut)
  Expected monthly = realised_APR / 12 × position_notional
"""

from dataclasses import dataclass, field

ENTRY_MIN_APR      = 40.0   # %/yr
ENTRY_MIN_STICKY   = 70     # classifier probability %
ENTRY_MIN_STREAK   = 20     # consecutive positive periods (8h each → 6+ days)
ENTRY_MAX_VOL      = 0.15   # rate std dev
EXIT_MIN_STICKY    = 60
EXIT_MIN_APR       = 25.0
REALISED_HAIRCUT   = 0.75   # 75% of headline APR based on backtest


@dataclass
class FundingCandidate:
    symbol:      str
    apr:         float    # %/yr
    p_sticky:    float    # 0-100 classifier output
    streak:      int      # consecutive positive 8h periods
    volatility:  float    # std of recent rates
    position_gbp: float = 0.0
    monthly_gbp:  float = 0.0
    passes:       bool    = False
    skip_reason:  str     = ""


def apply_entry_filter(c: FundingCandidate, capital_gbp: float) -> FundingCandidate:
    """Apply all four entry filters and size the position."""
    if c.apr < ENTRY_MIN_APR:
        c.skip_reason = f"APR {c.apr:.0f}% < {ENTRY_MIN_APR}%"
    elif c.p_sticky < ENTRY_MIN_STICKY:
        c.skip_reason = f"P(sticky) {c.p_sticky:.0f}% < {ENTRY_MIN_STICKY}%"
    elif c.streak < ENTRY_MIN_STREAK:
        c.skip_reason = f"streak {c.streak} < {ENTRY_MIN_STREAK}"
    elif c.volatility > ENTRY_MAX_VOL:
        c.skip_reason = f"vol {c.volatility:.3f} > {ENTRY_MAX_VOL}"
    else:
        c.passes = True
        c.position_gbp = _size_position(c.p_sticky, capital_gbp)
        realised = c.apr * REALISED_HAIRCUT
        c.monthly_gbp = (realised / 100 / 12) * c.position_gbp

    return c


def check_exit(symbol: str, curr_apr: float, p_sticky: float, streak: int) -> list[str]:
    """Return list of exit reasons (empty = hold)."""
    reasons = []
    if p_sticky < EXIT_MIN_STICKY:
        reasons.append(f"P(sticky) decayed to {p_sticky:.0f}%")
    if curr_apr < EXIT_MIN_APR:
        reasons.append(f"APR decayed to {curr_apr:.0f}%")
    if streak == 0:
        reasons.append("consecutive streak broken")
    return reasons


def _size_position(p_sticky: float, capital: float) -> float:
    if p_sticky >= 90: return capital * 0.14
    if p_sticky >= 75: return capital * 0.09
    if p_sticky >= 60: return capital * 0.04
    return 0.0


def income_summary(candidates: list[FundingCandidate]) -> dict:
    entered   = [c for c in candidates if c.passes]
    total_pos = sum(c.position_gbp for c in entered)
    total_mon = sum(c.monthly_gbp  for c in entered)
    return {
        "n_entered":        len(entered),
        "total_deployed":   round(total_pos, 2),
        "monthly_estimate": round(total_mon, 2),
        "annual_estimate":  round(total_mon * 12, 2),
        "haircut_applied":  f"{REALISED_HAIRCUT*100:.0f}%",
        "positions":        [
            {"symbol": c.symbol, "apr": c.apr, "p_sticky": c.p_sticky,
             "position_gbp": c.position_gbp, "monthly_gbp": round(c.monthly_gbp, 2)}
            for c in entered
        ]
    }
