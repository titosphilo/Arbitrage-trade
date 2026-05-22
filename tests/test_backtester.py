"""Tests for backtester."""
import sys; sys.path.insert(0, "..")
from backtester.engine import run_single

def test_profitable_stable_funding():
    """Stable high funding, no price move → should be profitable."""
    rates  = [0.001] * 90   # 0.1%/8h for 30 days
    prices = [100.0] * 90   # stable price
    r = run_single(rates, prices, size_usd=100)
    assert r.trades[0].net_pnl > 0, f"Expected profit, got {r.trades[0].net_pnl}"

def test_stop_loss_triggers():
    """Big adverse price move should trigger stop."""
    rates  = [0.001] * 30
    prices = [100.0] * 5 + [125.0] * 25   # 25% adverse move for short
    r = run_single(rates, prices, size_usd=100, stop_loss_pct=0.20)
    assert "stop_loss" in r.trades[0].exit_reason

def test_funding_decay_exit():
    """Rate decaying below threshold should trigger exit."""
    rates  = [0.001]*10 + [0.00005]*20   # decays below threshold
    prices = [100.0] * 30
    r = run_single(rates, prices, size_usd=100, exit_threshold=0.0001)
    assert r.trades[0].exit_reason == "funding_below_threshold"

if __name__ == "__main__":
    test_profitable_stable_funding(); print("✅ profitable stable funding")
    test_stop_loss_triggers();        print("✅ stop loss triggers")
    test_funding_decay_exit();        print("✅ funding decay exit")
    print("All tests passed")
