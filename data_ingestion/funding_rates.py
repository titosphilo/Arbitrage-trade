"""Fetch and store perpetual funding rates from Binance."""
import asyncio, aiohttp, sqlite3, time
import sys; sys.path.insert(0, '..')
from config import BINANCE_BASE, DB_PATH

async def fetch_all_rates(session) -> list[dict]:
    async with session.get(f'{BINANCE_BASE}/premiumIndex') as r:
        data = await r.json()
    return [
        {
            'symbol':   m['symbol'],
            'rate_8h':  float(m.get('lastFundingRate', 0)) * 100,
            'ann_pct':  float(m.get('lastFundingRate', 0)) * 100 * 3 * 365,
            'mark_px':  float(m.get('markPrice', 0)),
            'index_px': float(m.get('indexPrice', 0)),
            'ts':       int(time.time()),
        }
        for m in data
    ]

async def fetch_history(session, symbol: str, limit=500) -> list[dict]:
    """Last N funding rate records for a symbol."""
    async with session.get(
        f'{BINANCE_BASE}/fundingRate',
        params={'symbol': symbol, 'limit': limit}
    ) as r:
        data = await r.json()
    return [
        {
            'symbol': d['symbol'],
            'rate_8h': float(d['fundingRate']) * 100,
            'ts': int(d['fundingTime']) // 1000,
        }
        for d in data
    ]

def save_snapshot(rates: list[dict], db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute('''CREATE TABLE IF NOT EXISTS funding_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER, symbol TEXT, rate_8h REAL,
        ann_pct REAL, mark_px REAL, index_px REAL)''')
    conn.executemany(
        'INSERT INTO funding_snapshots (ts,symbol,rate_8h,ann_pct,mark_px,index_px) VALUES (?,?,?,?,?,?)',
        [(r['ts'],r['symbol'],r['rate_8h'],r['ann_pct'],r['mark_px'],r['index_px']) for r in rates]
    )
    conn.commit(); conn.close()

async def run():
    async with aiohttp.ClientSession() as s:
        rates = await fetch_all_rates(s)
    save_snapshot(rates)
    print(f"Saved {len(rates)} funding rate snapshots")
    top = sorted(rates, key=lambda x: -x['ann_pct'])[:10]
    for r in top:
        print(f"  {r['symbol']:20} {r['ann_pct']:>8.1f}%/yr  ${r['mark_px']:.4f}")

if __name__ == '__main__':
    asyncio.run(run())
