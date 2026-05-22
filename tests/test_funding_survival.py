from datetime import datetime, timezone

from backtester.funding_survival import FundingPoint, row_to_point, summarize, survival_trades


def utc(day: int):
    return datetime(2026, 1, day, tzinfo=timezone.utc)


def test_survival_counts_entries_that_remain_above_threshold():
    points = [
        FundingPoint("COINUSDT", utc(1), 0.55),
        FundingPoint("COINUSDT", utc(31), 0.44),
        FundingPoint("METAUSDT", utc(1), 0.65),
        FundingPoint("METAUSDT", utc(31), 0.20),
    ]

    trades = survival_trades(points, entry_threshold_apr=0.40, horizon_days=30)
    result = summarize(trades)

    assert result["entries"] == 2
    assert result["survivors"] == 1
    assert result["survival_rate"] == 0.5


def test_row_to_point_annualizes_raw_funding_rate():
    point = row_to_point(
        {
            "symbol": "btcusdt",
            "timestamp": "2026-01-01T00:00:00Z",
            "fundingRate": "0.0004",
        }
    )

    assert point.symbol == "BTCUSDT"
    assert round(point.apr, 3) == 0.438
