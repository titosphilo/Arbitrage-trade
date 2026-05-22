#!/usr/bin/env python3
"""
Funding Arbitrage Research Engine — main runner.
Usage: python main.py [scan|backtest|paper|all]
"""
import asyncio, sys
from pathlib import Path

async def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    
    if cmd in ("scan", "all"):
        from dashboard.scanner import main as scan
        await scan()
    
    if cmd in ("paper", "all"):
        from dashboard.paper_portfolio import get_portfolio_summary
        p = get_portfolio_summary()
        print(f"\nPaper portfolio: {p['n_positions']} positions | "
              f"Collected: ${p['total_collected_usd']:.4f} (£{p['total_collected_gbp']:.4f})")
    
    if cmd in ("backtest", "all"):
        print("\nBacktest: run backtester/survival_test.py for Track 1 results")
        print("Requires historical funding data — fetch first with:")
        print("  python -m data_ingestion.funding")

if __name__ == "__main__":
    asyncio.run(main())
