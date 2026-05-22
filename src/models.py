from dataclasses import dataclass


@dataclass(frozen=True)
class FundingOpportunity:
    symbol: str
    funding_apr: float
    daily_volume_usd: float
    annualized_volatility: float
    funding_persistence: float
    category: str = "crypto"


@dataclass(frozen=True)
class AccountConfig:
    equity_gbp: float = 2_000.0
    max_position_pct: float = 0.10
    max_symbol_risk_pct: float = 0.03
    min_daily_volume_usd: float = 5_000_000.0
    min_funding_apr: float = 0.40
    max_annualized_volatility: float = 1.80
