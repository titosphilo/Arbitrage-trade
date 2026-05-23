"""
Portfolio Safety Engine

Hard limits enforced BEFORE any trade is placed.
If any limit is breached, the trade is blocked regardless of signal quality.

Limits for a £2,000 account:
  max_position_pct:     15%  per coin  (£300)
  max_category_pct:     35%  per category (stock_perp / crypto / etc)
  max_total_leverage:   2.0x overall portfolio
  max_daily_drawdown:   5%   of account (£100 on £2,000)
  max_correlation:      0.70 pairwise
  min_liquidity_usd:    500,000 24h volume
  min_liquidation_buf:  30%  distance to liquidation
"""

from dataclasses import dataclass, field
from typing import Optional

# ── Hard limits ────────────────────────────────────────────────────
MAX_POSITION_PCT    = 0.15   # per coin
MAX_CATEGORY_PCT    = 0.35   # per category
MAX_TOTAL_LEVERAGE  = 2.0
MAX_DAILY_DD_PCT    = 0.05   # 5% of account
MAX_CORRELATION     = 0.70
MIN_LIQUIDITY_USD   = 500_000
MIN_LIQ_BUFFER_PCT  = 0.30   # 30% buffer before liquidation


@dataclass
class PortfolioState:
    capital_gbp:      float
    positions:        list[dict]   = field(default_factory=list)
    daily_pnl_gbp:    float        = 0.0

    def total_deployed(self) -> float:
        return sum(p.get('notional_gbp', 0) for p in self.positions)

    def deployed_pct(self) -> float:
        return self.total_deployed() / max(self.capital_gbp, 1)

    def category_deployed(self, category: str) -> float:
        return sum(p.get('notional_gbp', 0) for p in self.positions
                   if p.get('category') == category)

    def category_pct(self, category: str) -> float:
        return self.category_deployed(category) / max(self.capital_gbp, 1)

    def avg_leverage(self) -> float:
        if not self.positions: return 1.0
        return sum(p.get('leverage', 1) * p.get('notional_gbp', 0)
                   for p in self.positions) / max(self.total_deployed(), 1)

    def daily_dd_pct(self) -> float:
        return abs(min(self.daily_pnl_gbp, 0)) / max(self.capital_gbp, 1)


@dataclass
class SafetyCheck:
    passed:     bool
    blocked_by: list[str]   = field(default_factory=list)
    warnings:   list[str]   = field(default_factory=list)


def check_trade(
    symbol:        str,
    notional_gbp:  float,
    leverage:      float,
    category:      str,
    volume_24h_usd: float,
    mark_price:    float,
    liquidation_price: float,
    portfolio:     PortfolioState,
) -> SafetyCheck:
    """
    Run all safety checks before placing a trade.
    Returns SafetyCheck with passed=True only if ALL hard limits clear.
    """
    blocked  = []
    warnings = []

    # 1. Max position size
    pos_pct = notional_gbp / max(portfolio.capital_gbp, 1)
    if pos_pct > MAX_POSITION_PCT:
        blocked.append(
            f"Position {pos_pct*100:.1f}% > max {MAX_POSITION_PCT*100:.0f}% — "
            f"reduce to £{portfolio.capital_gbp * MAX_POSITION_PCT:.0f}"
        )

    # 2. Category concentration
    new_cat_pct = (portfolio.category_deployed(category) + notional_gbp) / portfolio.capital_gbp
    if new_cat_pct > MAX_CATEGORY_PCT:
        blocked.append(
            f"Category '{category}' would reach {new_cat_pct*100:.1f}% > max {MAX_CATEGORY_PCT*100:.0f}%"
        )

    # 3. Portfolio leverage
    new_total     = portfolio.total_deployed() + notional_gbp
    weighted_lev  = (portfolio.avg_leverage() * portfolio.total_deployed()
                     + leverage * notional_gbp) / max(new_total, 1)
    if weighted_lev > MAX_TOTAL_LEVERAGE:
        blocked.append(
            f"Portfolio leverage would reach {weighted_lev:.2f}x > max {MAX_TOTAL_LEVERAGE}x"
        )

    # 4. Daily drawdown
    if portfolio.daily_dd_pct() > MAX_DAILY_DD_PCT:
        blocked.append(
            f"Daily drawdown {portfolio.daily_dd_pct()*100:.1f}% > max {MAX_DAILY_DD_PCT*100:.0f}% — "
            f"no new trades until tomorrow"
        )

    # 5. Liquidity
    if volume_24h_usd < MIN_LIQUIDITY_USD:
        blocked.append(
            f"24h volume ${volume_24h_usd:,.0f} < min ${MIN_LIQUIDITY_USD:,.0f}"
        )

    # 6. Liquidation buffer
    if mark_price > 0 and liquidation_price > 0:
        liq_buffer = abs(mark_price - liquidation_price) / mark_price
        if liq_buffer < MIN_LIQ_BUFFER_PCT:
            blocked.append(
                f"Liquidation buffer {liq_buffer*100:.1f}% < min {MIN_LIQ_BUFFER_PCT*100:.0f}%"
            )

    # Soft warnings
    if portfolio.deployed_pct() > 0.60:
        warnings.append(f"Portfolio {portfolio.deployed_pct()*100:.0f}% deployed — approaching limit")
    if leverage > 1.5:
        warnings.append(f"Leverage {leverage}x — monitor closely")

    return SafetyCheck(passed=len(blocked) == 0, blocked_by=blocked, warnings=warnings)


# ── Decay exit model ──────────────────────────────────────────────

def decay_exit_signal(
    symbol:           str,
    curr_apr:         float,
    entry_apr:        float,
    streak:           int,
    prev_streak:      int,
    rate_vol_now:     float,
    rate_vol_entry:   float,
    oi_change_pct:    float,   # % OI change last 24h (negative = dropping)
    p_sticky_now:     float,
    p_sticky_entry:   float,
) -> dict:
    """
    Predict whether funding is about to fade. Exit if any exit trigger fires.
    
    Returns: {exit: bool, urgency: LOW/MEDIUM/HIGH, reasons: list}
    """
    reasons  = []
    urgency  = "LOW"

    # Hard exits (close immediately)
    if curr_apr < 0:
        reasons.append(f"Rate flipped negative ({curr_apr:.1f}%/yr)")
        urgency = "HIGH"
    if streak == 0 and prev_streak > 0:
        reasons.append("Consecutive positive streak just broke")
        urgency = "HIGH"
    if curr_apr < 15:
        reasons.append(f"APR {curr_apr:.0f}% below minimum viable threshold (15%)")
        urgency = "HIGH"

    # Soft exits (close within 1-2 periods)
    if p_sticky_now < 60 and p_sticky_entry >= 75:
        reasons.append(f"P(sticky) decayed {p_sticky_entry:.0f}% → {p_sticky_now:.0f}%")
        urgency = max(urgency, "MEDIUM") if urgency != "HIGH" else "HIGH"

    if curr_apr < entry_apr * 0.40:
        reasons.append(f"APR decayed to {curr_apr:.0f}% — less than 40% of entry {entry_apr:.0f}%")
        urgency = max(urgency, "MEDIUM") if urgency != "HIGH" else "HIGH"

    if rate_vol_now > rate_vol_entry * 2.5:
        reasons.append(f"Rate volatility spiked {rate_vol_now:.3f} vs entry {rate_vol_entry:.3f}")
        urgency = max(urgency, "MEDIUM") if urgency != "HIGH" else "HIGH"

    if oi_change_pct < -0.25:
        reasons.append(f"OI dropped {oi_change_pct*100:.0f}% in 24h — longs exiting")
        urgency = max(urgency, "MEDIUM") if urgency != "HIGH" else "HIGH"

    return {
        "symbol":   symbol,
        "exit":     len(reasons) > 0,
        "urgency":  urgency,
        "reasons":  reasons,
        "curr_apr": curr_apr,
        "streak":   streak,
    }


# ── Example ───────────────────────────────────────────────────────
if __name__ == "__main__":
    # Portfolio state
    portfolio = PortfolioState(
        capital_gbp   = 2000.0,
        daily_pnl_gbp = -30.0,
        positions = [
            {"symbol":"BUSDT",    "notional_gbp":280, "leverage":1.0, "category":"niche_crypto"},
            {"symbol":"TRUTHUSDT","notional_gbp":200, "leverage":1.0, "category":"niche_crypto"},
        ]
    )

    print("="*60)
    print("  SAFETY ENGINE — pre-trade check")
    print("="*60)

    # Test: add a new position
    result = check_trade(
        symbol="RAVEUSDT", notional_gbp=300, leverage=2.0,
        category="niche_crypto", volume_24h_usd=800_000,
        mark_price=0.05, liquidation_price=0.035,
        portfolio=portfolio
    )
    print(f"\n  RAVEUSDT £300 at 2x leverage:")
    print(f"  Passed: {'✅' if result.passed else '❌'}")
    for b in result.blocked_by: print(f"  BLOCKED: {b}")
    for w in result.warnings:   print(f"  WARNING: {w}")

    # Decay exit check (LYNUSDT — rate collapsed)
    print("\n  DECAY EXIT CHECK — LYNUSDT:")
    exit_sig = decay_exit_signal(
        symbol="LYNUSDT", curr_apr=22, entry_apr=2088,
        streak=3, prev_streak=30,
        rate_vol_now=0.45, rate_vol_entry=0.08,
        oi_change_pct=-0.40,
        p_sticky_now=12, p_sticky_entry=75
    )
    print(f"  Exit: {'YES ❌' if exit_sig['exit'] else 'NO ✅'}  Urgency: {exit_sig['urgency']}")
    for r in exit_sig['reasons']: print(f"  → {r}")
