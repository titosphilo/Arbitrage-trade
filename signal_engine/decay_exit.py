"""
Decay Exit Model — v2

Predicts when a funding trade should be closed BEFORE the rate flips negative.
Companion to quality_filter.py (entry) and position_sizer.py (sizing).

Key insight from first test:
  Floor rate (5.5%/yr) should NOT trigger exit for P(sticky)>75% coins.
  The floor IS the natural state for truly sticky names.
  Exit only fires when P(sticky) drops OR streak breaks — not just low APR.

Three exit tiers:
  HARD_EXIT  → close immediately, edge is gone
  SOFT_EXIT  → reduce 50%, monitor daily
  HOLD       → maintain position
"""

import numpy as np
from dataclasses import dataclass, field

BINANCE_FLOOR_APR   = 6.0    # %/yr — Binance minimum funding rate
HARD_EXIT_APR_WEAK  = 15.0   # %/yr exit threshold for P(sticky) < 75%
SOFT_EXIT_APR_DROP  = 0.40   # 40% drop from entry APR
SOFT_EXIT_SLOPE     = -0.015 # rate velocity threshold
OI_DROP_THRESHOLD   = -0.25  # -25% OI in 7 days


@dataclass
class ExitSignal:
    symbol:    str
    curr_apr:  float
    entry_apr: float
    streak:    int
    p_sticky:  float
    signal:    str    # HOLD / SOFT_EXIT / HARD_EXIT
    urgency:   str    # LOW / MEDIUM / HIGH
    action:    str    # HOLD / REDUCE_50 / CLOSE
    reasons:   list[str] = field(default_factory=list)


def rate_velocity(rates: list[float], n: int = 5) -> float:
    if len(rates) < 2: return 0.0
    r = rates[-min(n, len(rates)):]
    return float(np.polyfit(range(len(r)), r, 1)[0])


def check_exit(
    symbol:    str,
    curr_apr:  float,
    entry_apr: float,
    streak:    int,
    rate_hist: list[float],
    p_sticky:  float = 75.0,
    oi_chg:    float = 0.0,
) -> ExitSignal:

    reasons = []; signal = "HOLD"; urgency = "LOW"

    # ── P(sticky) hard floor — always close if classifier lost confidence ──
    if p_sticky < 50:
        reasons.append(f"P(sticky) {p_sticky:.0f}% < 50% — classifier no longer confident")
        signal = "HARD_EXIT"; urgency = "HIGH"

    # ── Streak broken — close immediately ─────────────────────────────────
    if streak == 0:
        reasons.append("Consecutive positive streak broken")
        signal = "HARD_EXIT"; urgency = "HIGH"

    # ── APR hard exit — only for weak coins (P < 75%) ─────────────────────
    # For sticky coins (P >= 75%), the floor rate IS the natural state
    if curr_apr < HARD_EXIT_APR_WEAK and p_sticky < 75:
        reasons.append(f"APR {curr_apr:.0f}%/yr < {HARD_EXIT_APR_WEAK:.0f}% (and P={p_sticky:.0f}% < 75%)")
        signal = "HARD_EXIT"; urgency = "HIGH"

    # ── Soft exit signals (only check if not already hard exit) ───────────
    if signal == "HOLD":
        vel  = rate_velocity(rate_hist)
        drop = (entry_apr - curr_apr) / max(entry_apr, 1)

        # Significant APR collapse from entry (not just floor rate)
        if drop > SOFT_EXIT_APR_DROP and entry_apr > BINANCE_FLOOR_APR * 2:
            reasons.append(f"APR dropped {drop*100:.0f}% from entry ({entry_apr:.0f}% → {curr_apr:.0f}%)")
            signal = "SOFT_EXIT"; urgency = "MEDIUM"

        # Rate velocity turning negative
        if vel < SOFT_EXIT_SLOPE:
            reasons.append(f"Rate velocity: {vel:.4f}/period (decaying trend)")
            urgency = "HIGH" if signal == "SOFT_EXIT" else "MEDIUM"
            signal  = "SOFT_EXIT"

        # OI collapsing
        if oi_chg < OI_DROP_THRESHOLD:
            reasons.append(f"OI dropped {abs(oi_chg)*100:.0f}% — longs exiting")
            signal  = "SOFT_EXIT"
            urgency = "MEDIUM" if urgency == "LOW" else urgency

    action = {"HARD_EXIT": "CLOSE", "SOFT_EXIT": "REDUCE_50", "HOLD": "HOLD"}[signal]
    return ExitSignal(symbol, curr_apr, entry_apr, streak, p_sticky, signal, urgency, action, reasons)


if __name__ == "__main__":
    tests = [
        ("LYNUSDT",       35,  2088, 22, [0.48,0.35,0.22,0.18,0.12,0.10,0.09], 12, -0.45),
        ("RAVEUSDT",      12,   548, 15, [0.12,0.10,0.08,0.06,0.05,0.04,0.04], 49, -0.15),
        ("BUSDT",        5.5,   5.5, 90, [0.005]*7,  90,  0.02),   # floor, sticky → HOLD
        ("TRUTHUSDT",    5.5,   5.5, 85, [0.005]*7,  83,  0.01),   # floor, sticky → HOLD
        ("JELLYJELLYUSDT",5.5, 1541, 30, [0.18,0.12,0.08,0.06,0.005,0.005,0.005], 68, -0.10),
    ]
    sigs = sorted([check_exit(*t) for t in tests], key=lambda s:{"HIGH":0,"MEDIUM":1,"LOW":2}[s.urgency])

    print("="*62)
    print("  DECAY EXIT MODEL v2 — current portfolio")
    print("="*62)
    for s in sigs:
        icon = "🔴" if s.signal=="HARD_EXIT" else ("🟡" if s.signal=="SOFT_EXIT" else "🟢")
        print(f"\n  {icon} {s.symbol:22} → {s.action:12} [{s.urgency}]")
        print(f"     {s.entry_apr:.0f}%→{s.curr_apr:.0f}%/yr  streak={s.streak}  P={s.p_sticky:.0f}%")
        for r in s.reasons: print(f"     ✗ {r}")
        if not s.reasons:   print(f"     ✓ Floor rate acceptable at P={s.p_sticky:.0f}% — hold")
