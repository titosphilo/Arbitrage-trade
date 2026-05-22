"""Position sizing and portfolio risk controls."""
import numpy as np
from config import MAX_POSITION_PCT, MAX_PORTFOLIO_PCT, LIQUIDATION_BUFFER, MAX_CORRELATION

def max_position_size(capital: float, score: float, ann_pct: float) -> float:
    """Size a position based on score and return. Higher score = larger size."""
    base_pct = MAX_POSITION_PCT
    # Reduce size for lower scores
    if score < 65:   base_pct *= 0.5
    elif score < 80: base_pct *= 0.75
    return capital * base_pct

def liquidation_distance(mark_price: float, leverage: float = 2.0) -> float:
    """% move that triggers liquidation at given leverage."""
    return (1 / leverage - LIQUIDATION_BUFFER) * 100

def portfolio_concentration(positions: list[dict]) -> dict:
    """Check portfolio-level risk."""
    total_notional = sum(p['notional_usd'] for p in positions)
    by_sector = {}
    for p in positions:
        sector = p.get('sector', 'other')
        by_sector[sector] = by_sector.get(sector, 0) + p['notional_usd']
    return {
        'total_deployed_pct': total_notional,
        'by_sector': {k: v/max(total_notional,1)*100 for k,v in by_sector.items()},
        'n_positions': len(positions),
    }

def pairwise_correlation(returns: dict[str, list[float]]) -> dict:
    """Compute pairwise correlation between position returns."""
    symbols = list(returns.keys())
    correlations = {}
    for i, s1 in enumerate(symbols):
        for s2 in symbols[i+1:]:
            r1 = np.array(returns[s1]); r2 = np.array(returns[s2])
            n = min(len(r1), len(r2))
            if n < 5: continue
            corr = float(np.corrcoef(r1[-n:], r2[-n:])[0, 1])
            correlations[f'{s1}/{s2}'] = corr
            if abs(corr) > MAX_CORRELATION:
                correlations[f'{s1}/{s2}_FLAG'] = 'HIGH_CORRELATION'
    return correlations
