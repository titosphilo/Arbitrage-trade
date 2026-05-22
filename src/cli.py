"""
Command-line interface for the arb research engine.

Usage:
    python -m src.cli sample     # show live sample of top opportunities
    python -m src.cli scan       # full scan + paper portfolio update
    python -m src.cli backtest   # run funding survival backtest
    python -m src.cli status     # current paper portfolio status
"""
import asyncio, sys, argparse
sys.path.insert(0, '.')

def sample():
    """Quick live scan — top 10 funding opportunities right now."""
    import asyncio, aiohttp, numpy as np
    from signal_engine.rank import Signal, compute_edge_score, estimate_flip_risk, rank_by_apr
    from config import STOCK_PERP_HEDGES

    async def run():
        async with aiohttp.ClientSession() as s:
            async with s.get('https://fapi.binance.com/fapi/v1/premiumIndex') as r:
                rates = await r.json()

        candidates = []
        for m in rates:
            sym  = m['symbol']
            rate = float(m.get('lastFundingRate', 0)) * 100
            ann  = rate * 3 * 365
            if ann < 10: continue
            flip = estimate_flip_risk([rate] * 5)
            sig = Signal(symbol=sym, funding_ann=ann, flip_risk=flip)
            sig.edge_score = compute_edge_score(sig)
            sig.classify()
            score = sig.edge_score
            action = sig.status
            hedge = STOCK_PERP_HEDGES.get(sym, {})
            candidates.append({
                'sym': sym, 'ann': ann, 'score': score,
                'action': action,
                'hedge': hedge.get('stock', '—'),
            })

        top = sorted(candidates, key=lambda x: -x['score'])[:10]
        print(f"\n{'Symbol':22} {'APR':>8} {'Score':>7} {'Action':>8}  Hedge")
        print('─' * 58)
        for c in top:
            icon = '✅' if c['action']=='ENTER' else ('🟡' if c['action']=='HOLD' else '⚪')
            print(f"{icon} {c['sym']:20} {c['ann']:>7.0f}%  {c['score']:>6.1f}  "
                  f"{c['action']:>8}  {c['hedge']}")
        print()

    asyncio.run(run())


def status():
    """Show current paper portfolio status from local DB."""
    import sqlite3, time
    from datetime import datetime
    try:
        conn = sqlite3.connect(
            '/root/.openclaw/workspace/projects/trading-bot/trading_data.db')
        positions = conn.execute("""
            SELECT f.symbol, f.entry_rate*3*365*100 ann, f.payments,
                   f.funding_collected/1.27 collected
            FROM funding_positions f WHERE f.status='open'
            ORDER BY f.funding_collected DESC
        """).fetchall()
        total = sum(p[3] for p in positions)
        first_ts = conn.execute("SELECT MIN(ts) FROM btc_price_1m").fetchone()[0]
        days = (int(time.time()) - first_ts) / 86400
        conn.close()

        print(f"\nPaper portfolio — Day {days:.0f}")
        print(f"{'Symbol':22} {'APR':>8} {'Payments':>9} {'Collected':>11}")
        print('─' * 55)
        for sym, ann, pmts, coll in positions:
            print(f"  {sym:20} {ann:>7.0f}%  {pmts:>8}   £{coll:>9.4f}")
        print(f"\n  Total: £{total:.4f}  |  £{total/days:.4f}/day  |  "
              f"£{total/days*30:.2f}/month")
    except Exception as e:
        print(f"DB not available: {e}")


def main():
    parser = argparse.ArgumentParser(description='Arb Research Engine')
    parser.add_argument('command', choices=['sample','scan','backtest','status'])
    args = parser.parse_args()

    if args.command == 'sample':   sample()
    elif args.command == 'status': status()
    elif args.command == 'scan':
        print("Full scan — coming in next PR (Codex backtest module)")
    elif args.command == 'backtest':
        print("Backtest — coming in next PR (Codex backtest module)")

if __name__ == '__main__':
    main()
