"""Fetch open interest and long/short ratios — crowding indicators."""
import asyncio, aiohttp

async def fetch_oi_history(session, symbol: str, period='1h', limit=30) -> list:
    async with session.get(
        'https://fapi.binance.com/futures/data/openInterestHist',
        params={'symbol': symbol, 'period': period, 'limit': limit}
    ) as r:
        data = await r.json()
    return [{'ts': int(d['timestamp'])//1000,
             'oi': float(d['sumOpenInterest']),
             'oi_usd': float(d['sumOpenInterestValue'])} for d in data]

async def fetch_ls_ratio(session, symbol: str, period='1h', limit=30) -> list:
    async with session.get(
        'https://fapi.binance.com/futures/data/globalLongShortAccountRatio',
        params={'symbol': symbol, 'period': period, 'limit': limit}
    ) as r:
        data = await r.json()
    return [{'ts': int(d['timestamp'])//1000,
             'ls_ratio': float(d['longShortRatio']),
             'long_pct': float(d['longAccount'])*100,
             'short_pct': float(d['shortAccount'])*100} for d in data]
