"""Fetch spot + perp prices, 24h stats, open interest."""
import asyncio, aiohttp, sqlite3, time
import sys; sys.path.insert(0, '..')
from config import BINANCE_BASE, DB_PATH

async def fetch_24h_stats(session, symbol: str) -> dict:
    async with session.get(
        f'{BINANCE_BASE}/ticker/24hr',
        params={'symbol': symbol}
    ) as r:
        d = await r.json()
    return {
        'symbol':    d.get('symbol'),
        'volume_usd': float(d.get('quoteVolume', 0)),
        'price_chg_pct': float(d.get('priceChangePercent', 0)),
        'high': float(d.get('highPrice', 0)),
        'low':  float(d.get('lowPrice', 0)),
    }

async def fetch_open_interest(session, symbol: str) -> float:
    async with session.get(
        f'{BINANCE_BASE}/openInterest',
        params={'symbol': symbol}
    ) as r:
        d = await r.json()
    return float(d.get('openInterest', 0))

async def fetch_long_short_ratio(session, symbol: str) -> float:
    """Global long/short ratio (crowding indicator)."""
    async with session.get(
        f'https://fapi.binance.com/futures/data/globalLongShortAccountRatio',
        params={'symbol': symbol, 'period': '1h', 'limit': 1}
    ) as r:
        d = await r.json()
    if d:
        return float(d[0].get('longShortRatio', 1.0))
    return 1.0

if __name__ == '__main__':
    async def test():
        async with aiohttp.ClientSession() as s:
            stats = await fetch_24h_stats(s, 'COINUSDT')
            oi    = await fetch_open_interest(s, 'COINUSDT')
            ls    = await fetch_long_short_ratio(s, 'COINUSDT')
            print(f"COINUSDT: vol=${stats['volume_usd']:,.0f}  OI={oi:.0f}  L/S={ls:.2f}")
    asyncio.run(test())
