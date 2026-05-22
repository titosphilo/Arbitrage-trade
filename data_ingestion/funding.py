"""Fetch and store perpetual funding rates from Binance."""
import asyncio, aiohttp, sqlite3, time
from config import BINANCE_BASE, DB_PATH

async def fetch_all_funding(session) -> list[dict]:
    async with session.get(f"{BINANCE_BASE}/premiumIndex",
        timeout=aiohttp.ClientTimeout(total=10)) as r:
        data = await r.json()
    return [{"symbol": m["symbol"],
             "funding_rate": float(m.get("lastFundingRate", 0)),
             "mark_price":   float(m.get("markPrice", 0)),
             "index_price":  float(m.get("indexPrice", 0)),
             "ts": int(time.time())}
            for m in data if float(m.get("lastFundingRate", 0)) != 0]

async def fetch_funding_history(session, symbol: str, limit=100) -> list[dict]:
    async with session.get(f"{BINANCE_BASE}/fundingRate",
        params={"symbol": symbol, "limit": limit},
        timeout=aiohttp.ClientTimeout(total=10)) as r:
        data = await r.json()
    return [{"symbol": symbol,
             "funding_rate": float(d["fundingRate"]),
             "ts": int(d["fundingTime"]) // 1000} for d in data]

def save_snapshot(records: list[dict]):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS funding_snapshots (
        id INTEGER PRIMARY KEY, ts INTEGER, symbol TEXT,
        funding_rate REAL, mark_price REAL, index_price REAL)""")
    conn.executemany(
        "INSERT INTO funding_snapshots (ts,symbol,funding_rate,mark_price,index_price) VALUES (?,?,?,?,?)",
        [(r["ts"],r["symbol"],r["funding_rate"],r["mark_price"],r["index_price"]) for r in records])
    conn.commit(); conn.close()

async def run():
    async with aiohttp.ClientSession() as s:
        records = await fetch_all_funding(s)
        save_snapshot(records)
        print(f"Saved {len(records)} funding rate records")

if __name__ == "__main__":
    asyncio.run(run())
