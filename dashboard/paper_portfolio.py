"""Paper portfolio tracker — simulates positions without live trading."""
import sqlite3, time, json
from config import DB_PATH, PAPER_CAPITAL_GBP, GBP_USD_RATE

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS paper_positions (
        id INTEGER PRIMARY KEY, symbol TEXT, opened_at INTEGER,
        entry_rate REAL, entry_price REAL, size_usd REAL,
        funding_collected REAL DEFAULT 0, payments INTEGER DEFAULT 0,
        status TEXT DEFAULT 'open', close_reason TEXT, closed_at INTEGER)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS paper_payments (
        id INTEGER PRIMARY KEY, symbol TEXT, ts INTEGER,
        rate REAL, amount_usd REAL)""")
    conn.commit(); conn.close()

def open_position(symbol: str, entry_rate: float, entry_price: float,
                   size_usd: float = 200.0):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO paper_positions
        (symbol,opened_at,entry_rate,entry_price,size_usd) VALUES (?,?,?,?,?)""",
        (symbol, int(time.time()), entry_rate, entry_price, size_usd))
    conn.commit(); conn.close()

def accrue_funding(symbol: str, current_rate: float, current_price: float):
    conn = sqlite3.connect(DB_PATH)
    pos = conn.execute(
        "SELECT id,size_usd FROM paper_positions WHERE symbol=? AND status='open'",
        (symbol,)).fetchone()
    if not pos: conn.close(); return
    amount = current_rate * pos[1]
    conn.execute("UPDATE paper_positions SET funding_collected=funding_collected+?, payments=payments+1 WHERE id=?",
        (amount, pos[0]))
    conn.execute("INSERT INTO paper_payments (symbol,ts,rate,amount_usd) VALUES (?,?,?,?)",
        (symbol, int(time.time()), current_rate, amount))
    conn.commit(); conn.close()

def get_portfolio_summary() -> dict:
    conn = sqlite3.connect(DB_PATH)
    positions = [dict(zip(["id","symbol","opened_at","entry_rate","entry_price",
                            "size_usd","funding_collected","payments","status"],r))
                 for r in conn.execute(
        "SELECT id,symbol,opened_at,entry_rate,entry_price,size_usd,funding_collected,payments,status "
        "FROM paper_positions WHERE status='open'").fetchall()]
    conn.close()
    total_collected = sum(p["funding_collected"] for p in positions)
    total_deployed  = sum(p["size_usd"] for p in positions)
    return {"positions": positions, "total_collected_usd": total_collected,
            "total_deployed_usd": total_deployed,
            "total_collected_gbp": total_collected / GBP_USD_RATE,
            "n_positions": len(positions)}
