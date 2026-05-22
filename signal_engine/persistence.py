"""Measure how consistently a coin pays positive funding.

Persistence score 0-100:
  100 = always positive (sticky)
  50  = 50/50 positive/negative
  0   = always negative
"""
import numpy as np

def persistence_score(history: list[float]) -> float:
    """history = list of 8h funding rates (most recent last)."""
    if not history: return 50.0
    positive = sum(1 for r in history if r > 0)
    return round(positive / len(history) * 100, 1)

def decay_rate(history: list[float], window=10) -> float:
    """How fast is the funding rate declining? Negative = declining."""
    if len(history) < window: return 0.0
    recent = np.mean(history[-window//2:])
    older  = np.mean(history[-window:-window//2])
    if older == 0: return 0.0
    return (recent - older) / abs(older) * 100

def flip_risk_score(history: list[float]) -> float:
    """Probability of funding flipping negative. 0=low risk, 100=high."""
    if len(history) < 5: return 50.0
    recent_rates = history[-5:]
    trend = np.polyfit(range(len(recent_rates)), recent_rates, 1)[0]
    current = history[-1] if history else 0
    if current <= 0:   return 100.0
    if trend < -0.0001: return min(90, 50 + abs(trend) * 100000)
    return max(0, 20 - current * 1000)
