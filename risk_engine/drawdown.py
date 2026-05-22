"""Drawdown estimation and portfolio-level risk."""
import numpy as np

def max_drawdown(returns: list[float]) -> float:
    """Maximum drawdown from a list of period returns."""
    cumulative = np.cumprod([1 + r/100 for r in returns])
    rolling_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - rolling_max) / rolling_max * 100
    return float(np.min(drawdown))

def estimate_worst_case(funding_ann: float, price_move_pct: float,
                         position_pct: float) -> float:
    """Worst-case monthly loss if price moves adversely."""
    funding_monthly = funding_ann / 12 * position_pct / 100
    price_loss      = price_move_pct * position_pct / 100
    return funding_monthly - price_loss

def portfolio_var(positions: list[dict], confidence=0.95) -> float:
    """Simple VaR estimate for the portfolio."""
    total_notional = sum(p.get("notional_usd", 0) for p in positions)
    avg_vol = 0.05  # 5% daily vol assumed for perps
    z = 1.645 if confidence == 0.95 else 2.326
    return total_notional * avg_vol * z
