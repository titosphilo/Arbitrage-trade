from src.models import AccountConfig, FundingOpportunity
from src.risk import max_position_notional_gbp, monthly_funding_income_gbp, risk_flags


def test_monthly_funding_income_gbp():
    assert monthly_funding_income_gbp(100, 1.20) == 10


def test_position_size_respects_concentration_cap():
    opportunity = FundingOpportunity("AMZNUSDT", 1.0, 20_000_000, 0.5, 0.8)
    assert max_position_notional_gbp(AccountConfig(equity_gbp=2_000), opportunity) == 120


def test_risk_flags_low_liquidity():
    opportunity = FundingOpportunity("CBRSUSDT", 0.89, 1_000_000, 1.0, 0.8)
    assert "low_liquidity" in risk_flags(AccountConfig(), opportunity)
