"""Tests for signal engine rank and scoring."""
import sys; sys.path.insert(0, '..')
from signal_engine.rank import compute_score, classify, estimate_flip_risk

def test_high_apr_high_persistence():
    score = compute_score(ann_pct=140, persistence=1.0,
                          volume_usd=5e6, oi_usd=2e6,
                          ls_ratio=2.0, flip_risk=0.05)
    assert score >= 70, f"Expected score >= 70, got {score}"
    assert classify(score, 140) == 'ENTER'

def test_low_apr_exits():
    score = compute_score(ann_pct=5, persistence=0.5,
                          volume_usd=1e6, oi_usd=5e5,
                          ls_ratio=1.2, flip_risk=0.4)
    assert classify(score, 5) in ('EXIT', 'WATCH', 'SKIP')

def test_flip_risk_from_history():
    # All positive → low flip risk
    risk = estimate_flip_risk([0.1, 0.2, 0.15, 0.18, 0.12])
    assert risk < 0.2

    # Alternating → high flip risk
    risk = estimate_flip_risk([0.1, -0.1, 0.1, -0.1, 0.1])
    assert risk > 0.5

if __name__ == '__main__':
    test_high_apr_high_persistence()
    test_low_apr_exits()
    test_flip_risk_from_history()
    print("All tests passed ✅")
