"""
Live opportunity scanner — the main entry point.
Run this to see current best opportunities with scores.
"""
import asyncio, aiohttp, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_ingestion.funding import fetch_all_funding
from data_ingestion.basis import compute_all
from signal_engine.rank import from_funding_records, rank_by_apr
from signal_engine.filters import liquidity_score, crowding_score
from risk_engine.correlation import is_too_correlated, get_sector
from config import STOCK_PERP_HEDGES, ENTER_FUNDING_APR, PAPER_CAPITAL_GBP

async def scan() -> list[dict]:
    async with aiohttp.ClientSession() as s:
        records = await fetch_all_funding(s)
    
    basis_metrics = compute_all(records)
    basis_map = {b.symbol: b for b in basis_metrics}
    signals = from_funding_records(records)
    
    results = []
    for sig in signals:
        if sig.funding_ann < 5: continue
        bm = basis_map.get(sig.symbol)
        hedge = STOCK_PERP_HEDGES.get(sig.symbol, {})
        results.append({
            "symbol":       sig.symbol,
            "funding_ann":  round(sig.funding_ann, 1),
            "basis_ann":    round(bm.annualised_basis if bm else 0, 1),
            "total_edge":   round(sig.funding_ann + (bm.annualised_basis if bm else 0), 1),
            "status":       sig.status,
            "edge_score":   round(sig.edge_score, 1),
            "stock_hedge":  hedge.get("stock", ""),
            "etf_hedge":    hedge.get("etf", ""),
            "sector":       get_sector(sig.symbol),
            "is_stock_perp": sig.symbol in STOCK_PERP_HEDGES,
        })
    
    return sorted(results, key=lambda x: -x["total_edge"])


def print_report(opportunities: list[dict], account_gbp=PAPER_CAPITAL_GBP):
    print(f"\n{'='*70}")
    print(f"  FUNDING ARB SCANNER — {time.strftime('%d %b %Y %H:%M UTC', time.gmtime())}")
    print(f"{'='*70}")
    
    enter  = [o for o in opportunities if o["status"] == "ENTER"]
    hold   = [o for o in opportunities if o["status"] == "HOLD"]
    
    print(f"\n  ENTER signals ({len(enter)}):")
    print(f"  {'Symbol':20} {'Ann%':>8} {'Basis':>7} {'Edge':>6} {'Hedge':>25} {'Sector'}")
    print(f"  {'─'*75}")
    for o in enter[:10]:
        hedge = f"{o['stock_hedge']} / {o['etf_hedge']}" if o['stock_hedge'] else "—"
        print(f"  {'✅':2} {o['symbol']:18} {o['funding_ann']:>7.0f}%  {o['basis_ann']:>+6.1f}%  "
              f"{o['total_edge']:>5.0f}%  {hedge:25} {o['sector']}")
    
    if hold:
        print(f"\n  HOLD signals ({len(hold)}):")
        for o in hold[:5]:
            print(f"  {'🟡':2} {o['symbol']:18} {o['funding_ann']:>7.0f}%/yr")
    
    # Income estimate
    if enter:
        per_pos = account_gbp * 0.10
        n = min(len(enter), 6)
        avg_apr = sum(o['funding_ann'] for o in enter[:n]) / n
        gross_monthly = avg_apr / 12 * per_pos * n / 100
        net_monthly = gross_monthly * 0.50  # 50% haircut
        print(f"\n  INCOME ESTIMATE (£{account_gbp:,.0f} account, 10% per position):")
        print(f"  Positions: {n} | Avg APR: {avg_apr:.0f}% | "
              f"Gross: £{gross_monthly:.0f}/mo | Net (50% haircut): £{net_monthly:.0f}/mo")
    
    # Correlation warning
    stock_perp_syms = [o['symbol'] for o in enter if o['is_stock_perp']]
    if len(stock_perp_syms) > 2:
        too_corr, pairs = is_too_correlated(stock_perp_syms)
        if too_corr:
            print(f"\n  ⚠️  CORRELATION WARNING:")
            for a, b, c in pairs[:3]:
                print(f"     {a} ↔ {b}: {c:.0%} (consider reducing concentration)")


async def main():
    opps = await scan()
    print_report(opps)
    return opps

if __name__ == "__main__":
    asyncio.run(main())
