"""CLI for the Arbitrage Research Engine. Usage: python -m src.cli <command> [path]"""
import argparse, asyncio, csv, sys
sys.path.insert(0, '.')


def sample():
    from signal_engine.rank import Signal, compute_edge_score, estimate_flip_risk
    from config import STOCK_PERP_HEDGES
    import aiohttp

    async def run():
        async with aiohttp.ClientSession() as s:
            async with s.get('https://fapi.binance.com/fapi/v1/premiumIndex') as r:
                rates = await r.json()
        candidates = []
        for m in rates:
            sym  = m['symbol']; rate = float(m.get('lastFundingRate', 0)) * 100
            ann  = rate * 3 * 365
            if ann < 10: continue
            flip = estimate_flip_risk([rate] * 5)
            sig  = Signal(symbol=sym, funding_ann=ann, flip_risk=flip)
            sig.edge_score = compute_edge_score(sig); sig.classify()
            candidates.append({'sym':sym,'ann':ann,'score':sig.edge_score,
                                'action':sig.status,
                                'hedge':STOCK_PERP_HEDGES.get(sym,{}).get('stock','—')})
        top = sorted(candidates, key=lambda x: -x['score'])[:10]
        print(f"\n{'Symbol':22} {'APR':>8} {'Score':>7} {'Action':>8}  Hedge")
        print('─'*58)
        for c in top:
            icon = '✅' if c['action']=='ENTER' else ('🟡' if c['action']=='HOLD' else '⚪')
            print(f"{icon} {c['sym']:20} {c['ann']:>7.0f}%  {c['score']:>6.1f}  "
                  f"{c['action']:>8}  {c['hedge']}")
        print()
    asyncio.run(run())


def status():
    import sqlite3, time
    try:
        conn = sqlite3.connect('/root/.openclaw/workspace/projects/trading-bot/trading_data.db')
        positions = conn.execute("""SELECT f.symbol, f.entry_rate*3*365*100,
            f.payments, f.funding_collected/1.27
            FROM funding_positions f WHERE f.status='open'
            ORDER BY f.funding_collected DESC""").fetchall()
        total   = sum(p[3] for p in positions)
        first   = conn.execute("SELECT MIN(ts) FROM btc_price_1m").fetchone()[0]
        days    = (int(time.time())-first)/86400; conn.close()
        print(f"\nPaper portfolio — Day {days:.0f}")
        print(f"{'Symbol':22} {'APR':>8} {'Pmts':>6} {'Collected':>11}")
        print('─'*52)
        for sym,ann,pmts,coll in positions:
            print(f"  {sym:20} {ann:>7.0f}%  {pmts:>5}   £{coll:>9.4f}")
        print(f"\n  Total: £{total:.4f}  |  £{total/days:.4f}/day  |  £{total/days*30:.2f}/month")
    except Exception as e: print(f"DB error: {e}")


def funding_survival_cmd(path):
    from backtester.funding_survival import run_backtest
    syms = set()
    with open(path) as f:
        for row in csv.DictReader(f): syms.add(row['symbol'])
    print(f"\n  Funding Survival Backtest — 40%/yr threshold | {len(syms)} symbols")
    print(f"  {'Symbol':22} {'Entries':>8} {'Survival':>9} {'Realised%/yr':>13} {'vs Headline':>12}")
    print(f"  {'─'*68}")
    for sym in sorted(syms)[:25]:
        r = run_backtest(sym)
        if r.get('n_entries',0)==0: continue
        icon = '✅' if r['survival_rate']>0.7 else ('⚠️' if r['survival_rate']>0.4 else '❌')
        print(f"  {icon} {sym:20} {r['n_entries']:>8} {r['survival_rate']*100:>8.0f}%  "
              f"{r['avg_ann_realised']:>12.1f}%  {r['realised_pct_of_headline']:>11.0f}%")


def persistence_cmd(path):
    from signal_engine.persistence import run
    from pathlib import Path; run(Path(path))


def main():
    p = argparse.ArgumentParser(description='Arb Research Engine')
    p.add_argument('command',
                   choices=['sample','funding-survival','persistence','status','scan'])
    p.add_argument('path', nargs='?', default=None)
    args = p.parse_args()

    if args.command == 'sample':
        sample()
    elif args.command == 'status':
        status()
    elif args.command == 'funding-survival':
        funding_survival_cmd(args.path or 'data/funding_history_166d.csv')
    elif args.command == 'persistence':
        persistence_cmd(args.path or 'data/persistence_features.csv')
    elif args.command == 'scan':
        sample()

if __name__ == '__main__':
    main()
