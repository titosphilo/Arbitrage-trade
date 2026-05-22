from signal_engine.rank import EdgeCandidate, compute_edge_score


def test_sticky_probability_increases_edge_score():
    candidate = EdgeCandidate(
        symbol="RAVEUSDT",
        funding_apr=0.75,
        rate_volatility=0.05,
        consecutive_positive_periods=90,
        oi_change_rate=0.10,
        coin_category="sticky_coin",
    )

    sticky = compute_edge_score(candidate, sticky_probability=0.90)
    fragile = compute_edge_score(candidate, sticky_probability=0.20)

    assert sticky.edge_score > fragile.edge_score
    assert sticky.sticky_probability == 0.90
