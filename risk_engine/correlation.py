"""Position correlation and concentration risk."""
import numpy as np

# Sector groupings for correlation estimation
SECTORS = {
    "crypto":  ["BTCUSDT","ETHUSDT","SOLUSDT","COINUSDT"],
    "tech":    ["AMZNUSDT","METAUSDT","GOOGLUSDT","MSFTUSDT"],
    "semis":   ["NVDAUSDT","QCOMUSDT","MRVLUSDT","INTCUSDT"],
    "ev":      ["TSLAUSDT"],
}

INTRA_SECTOR_CORR  = 0.70  # assumed within sector
CROSS_SECTOR_CORR  = 0.25  # assumed across sectors

def get_sector(symbol: str) -> str:
    for sector, syms in SECTORS.items():
        if symbol in syms: return sector
    return "other"

def portfolio_correlation_matrix(symbols: list[str]) -> np.ndarray:
    n = len(symbols)
    corr = np.eye(n)
    sectors = [get_sector(s) for s in symbols]
    for i in range(n):
        for j in range(i+1, n):
            c = INTRA_SECTOR_CORR if sectors[i] == sectors[j] else CROSS_SECTOR_CORR
            corr[i,j] = corr[j,i] = c
    return corr

def concentration_score(weights: list[float]) -> float:
    """Herfindahl index. 1.0 = fully concentrated, 1/n = equal weight."""
    return float(np.sum(np.array(weights)**2))

def is_too_correlated(symbols: list[str], threshold=0.70) -> tuple[bool, list]:
    corr = portfolio_correlation_matrix(symbols)
    n = len(symbols)
    flagged = []
    for i in range(n):
        for j in range(i+1, n):
            if corr[i,j] >= threshold:
                flagged.append((symbols[i], symbols[j], corr[i,j]))
    return len(flagged) > 0, flagged
