"""Compute futures basis (contango/backwardation) from mark vs index."""
from dataclasses import dataclass

@dataclass
class BasisMetrics:
    symbol: str
    mark_price: float
    index_price: float
    basis_pct: float
    annualised_basis: float

def compute_basis(mark: float, index: float, days_to_expiry=None) -> float:
    """Basis as % of index. Positive = contango (perp premium)."""
    if index == 0: return 0.0
    return (mark - index) / index * 100

def annualise_basis(basis_pct: float, periods_per_year=3*365) -> float:
    """Convert 8-hour basis to annualised rate."""
    return basis_pct * periods_per_year

def compute_all(records: list[dict]) -> list[BasisMetrics]:
    results = []
    for r in records:
        mark  = r.get("mark_price", 0)
        index = r.get("index_price", mark)
        basis = compute_basis(mark, index)
        results.append(BasisMetrics(
            symbol=r["symbol"], mark_price=mark, index_price=index,
            basis_pct=basis, annualised_basis=annualise_basis(basis)))
    return results
