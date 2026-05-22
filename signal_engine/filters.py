"""Liquidity, volatility, and crowding filters."""
import numpy as np
from config import MIN_OI_USD, MIN_VOLUME_USD

def liquidity_score(oi_usd: float, volume_usd: float) -> float:
    """Score 0-100. Higher OI and volume = better liquidity."""
    oi_score  = min(oi_usd / MIN_OI_USD, 10) * 5      # max 50
    vol_score = min(volume_usd / MIN_VOLUME_USD, 10) * 5  # max 50
    return round(min(100, oi_score + vol_score), 1)

def volatility_filter(prices: list[float], max_vol_pct=10.0) -> bool:
    """True = passes filter (low enough volatility)."""
    if len(prices) < 2: return True
    returns = np.diff(prices) / np.array(prices[:-1]) * 100
    vol = float(np.std(returns))
    return vol < max_vol_pct

def crowding_score(funding_rate: float, oi_change_pct: float = 0) -> float:
    """Score 0-100. High = crowded longs (good for shorts)."""
    rate_score = min(funding_rate * 100 * 3 * 365 / 2, 70)
    oi_score   = max(0, min(oi_change_pct * 2, 30))
    return round(min(100, rate_score + oi_score), 1)

def is_tradeable(oi_usd: float, volume_usd: float,
                 prices: list[float] = None) -> tuple[bool, str]:
    if oi_usd < MIN_OI_USD:
        return False, f"OI too low (${oi_usd:,.0f} < ${MIN_OI_USD:,.0f})"
    if volume_usd < MIN_VOLUME_USD:
        return False, f"Volume too low"
    if prices and not volatility_filter(prices):
        return False, "Volatility too high"
    return True, "OK"
