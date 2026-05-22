from .models import AccountConfig, FundingOpportunity


def max_position_notional_gbp(config: AccountConfig, opportunity: FundingOpportunity) -> float:
    concentration_cap = config.equity_gbp * config.max_position_pct
    volatility_cap = (config.equity_gbp * config.max_symbol_risk_pct) / max(
        opportunity.annualized_volatility, 0.01
    )
    return round(min(concentration_cap, volatility_cap), 2)


def monthly_funding_income_gbp(notional_gbp: float, funding_apr: float) -> float:
    return round(notional_gbp * funding_apr / 12, 2)


def risk_flags(config: AccountConfig, opportunity: FundingOpportunity) -> list[str]:
    flags: list[str] = []

    if opportunity.daily_volume_usd < config.min_daily_volume_usd:
        flags.append("low_liquidity")
    if opportunity.annualized_volatility > config.max_annualized_volatility:
        flags.append("high_volatility")
    if opportunity.funding_persistence < 0.50:
        flags.append("weak_persistence")
    if opportunity.funding_apr < config.min_funding_apr:
        flags.append("funding_below_threshold")

    return flags
