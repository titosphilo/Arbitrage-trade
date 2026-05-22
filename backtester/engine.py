"""
Funding Basket Backtester

Tests whether headline APR survives:
- Adverse price moves (mark-to-market PnL)
- Spread + fee costs
- Funding rate decay over time
- Stop rules (exit when funding drops below threshold)
"""
import numpy as np
from dataclasses import dataclass, field
from config import SPREAD_COST_PCT, FUNDING_HAIRCUT, HEDGE_ERROR_PCT

@dataclass
class Trade:
    symbol:       str
    entry_ts:     int
    entry_price:  float
    size_usd:     float
    direction:    str = "short"
    exit_ts:      int = 0
    exit_price:   float = 0.0
    exit_reason:  str = ""
    funding_collected: float = 0.0
    mtm_pnl:      float = 0.0
    fees:         float = 0.0

    @property
    def net_pnl(self) -> float:
        return self.funding_collected + self.mtm_pnl - self.fees

    @property
    def net_apr(self) -> float:
        if self.entry_ts == self.exit_ts or self.size_usd == 0: return 0.0
        days = (self.exit_ts - self.entry_ts) / 86400
        return self.net_pnl / self.size_usd / days * 365 * 100 if days > 0 else 0.0


@dataclass
class BacktestResult:
    trades:         list[Trade] = field(default_factory=list)
    gross_funding:  float = 0.0
    mtm_pnl:        float = 0.0
    total_fees:     float = 0.0
    win_rate:       float = 0.0
    avg_hold_days:  float = 0.0
    net_apr:        float = 0.0
    max_drawdown:   float = 0.0
    sharpe:         float = 0.0

    def summary(self) -> str:
        return (f"Trades: {len(self.trades)} | "
                f"Gross funding: {self.gross_funding:.2f}% | "
                f"MTM: {self.mtm_pnl:.2f}% | "
                f"Fees: {self.total_fees:.2f}% | "
                f"Net APR: {self.net_apr:.1f}% | "
                f"Win rate: {self.win_rate:.0f}% | "
                f"Max DD: {self.max_drawdown:.1f}%")


def run_single(
    funding_history: list[float],   # 8h rates, oldest first
    price_history:   list[float],   # prices at each funding period
    size_usd:        float = 100.0,
    exit_threshold:  float = 0.0001, # exit if rate < this (0.01%/8h = ~4%/yr)
    stop_loss_pct:   float = 0.20,   # 20% adverse price move → stop
) -> BacktestResult:
    """
    Simulate one position: short the perp, collect funding.
    Each period = 8 hours.
    """
    assert len(funding_history) == len(price_history), "History length mismatch"
    
    trade = Trade(
        symbol="SIM", entry_ts=0, entry_price=price_history[0],
        size_usd=size_usd, direction="short"
    )
    
    net_returns = []
    
    for i, (rate, price) in enumerate(zip(funding_history, price_history)):
        # Funding income (short receives positive funding)
        funding_income = rate * size_usd
        trade.funding_collected += funding_income
        
        # MTM PnL for short: profit when price falls, loss when rises
        price_chg = (trade.entry_price - price) / trade.entry_price
        current_mtm = price_chg * size_usd
        
        # Spread cost (entry only, once)
        if i == 0:
            trade.fees += SPREAD_COST_PCT * size_usd * 2  # entry + eventual exit
        
        net_this_period = funding_income + (current_mtm - trade.mtm_pnl)
        trade.mtm_pnl = current_mtm
        net_returns.append(net_this_period / size_usd * 100)
        
        # Stop rules
        adverse_move = (price - trade.entry_price) / trade.entry_price
        if adverse_move > stop_loss_pct:
            trade.exit_reason = f"stop_loss_{stop_loss_pct:.0%}"
            break
        if rate < exit_threshold:
            trade.exit_reason = "funding_below_threshold"
            break
        if i == len(funding_history) - 1:
            trade.exit_reason = "end_of_period"
    
    trade.exit_price = price_history[min(i, len(price_history)-1)]
    
    # Build result
    result = BacktestResult(trades=[trade])
    result.gross_funding = trade.funding_collected / size_usd * 100
    result.mtm_pnl       = trade.mtm_pnl / size_usd * 100
    result.total_fees     = trade.fees / size_usd * 100
    
    if net_returns:
        result.max_drawdown = float(min(np.cumsum(net_returns)))
        result.sharpe = (np.mean(net_returns) / np.std(net_returns) * np.sqrt(365*3)
                         if np.std(net_returns) > 0 else 0)
    
    days_held = len(funding_history) / 3  # 3 periods per day
    result.avg_hold_days = days_held
    result.net_apr = trade.net_pnl / size_usd / max(days_held, 1) * 365 * 100
    result.win_rate = 100.0 if trade.net_pnl > 0 else 0.0
    return result


def run_basket(
    basket: list[dict],   # [{symbol, funding_history, price_history}]
    size_per_position: float = 200.0,
    **kwargs
) -> dict:
    """Run backtest on a basket of positions."""
    results = {}
    total_pnl = 0.0
    
    for pos in basket:
        r = run_single(
            pos["funding_history"],
            pos["price_history"],
            size_usd=size_per_position,
            **kwargs
        )
        results[pos["symbol"]] = r
        total_pnl += r.trades[0].net_pnl if r.trades else 0
    
    return {
        "individual": results,
        "total_net_pnl": total_pnl,
        "total_deployed": size_per_position * len(basket),
        "portfolio_return_pct": total_pnl / (size_per_position * len(basket)) * 100,
    }
