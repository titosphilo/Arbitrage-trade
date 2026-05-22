import argparse
import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Iterable


SYMBOL_COLUMNS = ("symbol", "pair", "ticker", "contract")
TIME_COLUMNS = ("timestamp", "time", "funding_time", "fundingTime", "datetime", "date")
APR_COLUMNS = ("funding_apr", "apr", "annualized_apr", "annualized_rate")
RATE_COLUMNS = ("funding_rate", "fundingRate", "rate")


@dataclass(frozen=True)
class FundingPoint:
    symbol: str
    timestamp: datetime
    apr: float


@dataclass(frozen=True)
class SurvivalTrade:
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_apr: float
    exit_apr: float
    survived: bool


def parse_timestamp(value: object) -> datetime:
    if value is None:
        raise ValueError("missing timestamp")

    text = str(value).strip()
    if not text:
        raise ValueError("missing timestamp")

    if text.isdigit():
        numeric = int(text)
        if numeric > 10_000_000_000:
            numeric = numeric / 1000
        return datetime.fromtimestamp(numeric, tz=timezone.utc)

    normalized = text.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_float(value: object) -> float:
    if value is None:
        raise ValueError("missing numeric value")
    text = str(value).strip().replace("%", "")
    number = float(text)
    if "%" in str(value):
        return number / 100
    return number


def first_present(row: dict, candidates: Iterable[str]) -> object:
    for column in candidates:
        if column in row and row[column] not in (None, ""):
            return row[column]
    raise KeyError(f"missing one of: {', '.join(candidates)}")


def row_to_point(row: dict, periods_per_year: int = 1095) -> FundingPoint:
    symbol = str(first_present(row, SYMBOL_COLUMNS)).strip().upper()
    timestamp = parse_timestamp(first_present(row, TIME_COLUMNS))

    try:
        apr = parse_float(first_present(row, APR_COLUMNS))
    except KeyError:
        funding_rate = parse_float(first_present(row, RATE_COLUMNS))
        apr = funding_rate * periods_per_year

    return FundingPoint(symbol=symbol, timestamp=timestamp, apr=apr)


def load_csv(path: Path) -> list[FundingPoint]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [row_to_point(row) for row in reader]


def load_sqlite(path: Path, table: str | None = None) -> list[FundingPoint]:
    with sqlite3.connect(path) as connection:
        selected_table = table or detect_sqlite_table(connection)
        rows = connection.execute(f'SELECT * FROM "{selected_table}"').fetchall()
        columns = [description[0] for description in connection.execute(f'SELECT * FROM "{selected_table}" LIMIT 1').description]

    return [row_to_point(dict(zip(columns, row))) for row in rows]


def detect_sqlite_table(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    if not rows:
        raise ValueError("SQLite database has no tables")
    return str(rows[0][0])


def load_funding_history(path: str | Path, table: str | None = None) -> list[FundingPoint]:
    resolved = Path(path)
    suffix = resolved.suffix.lower()

    if suffix == ".csv":
        return load_csv(resolved)
    if suffix in {".db", ".sqlite", ".sqlite3"}:
        return load_sqlite(resolved, table)

    raise ValueError(f"unsupported funding history format: {resolved.suffix}")


def survival_trades(
    points: Iterable[FundingPoint],
    entry_threshold_apr: float = 0.40,
    horizon_days: int = 30,
) -> list[SurvivalTrade]:
    by_symbol: dict[str, list[FundingPoint]] = {}
    for point in points:
        by_symbol.setdefault(point.symbol, []).append(point)

    trades: list[SurvivalTrade] = []
    horizon = timedelta(days=horizon_days)

    for symbol, symbol_points in by_symbol.items():
        ordered = sorted(symbol_points, key=lambda point: point.timestamp)
        for index, entry in enumerate(ordered):
            if entry.apr < entry_threshold_apr:
                continue

            target_time = entry.timestamp + horizon
            exit_point = next(
                (
                    candidate
                    for candidate in ordered[index + 1 :]
                    if candidate.timestamp >= target_time
                ),
                None,
            )
            if exit_point is None:
                continue

            trades.append(
                SurvivalTrade(
                    symbol=symbol,
                    entry_time=entry.timestamp,
                    exit_time=exit_point.timestamp,
                    entry_apr=entry.apr,
                    exit_apr=exit_point.apr,
                    survived=exit_point.apr >= entry_threshold_apr,
                )
            )

    return trades


def summarize(trades: list[SurvivalTrade]) -> dict:
    if not trades:
        return {
            "entries": 0,
            "survivors": 0,
            "survival_rate": 0.0,
            "median_entry_apr": None,
            "median_exit_apr": None,
            "mean_exit_apr": None,
            "symbols": {},
        }

    survivors = [trade for trade in trades if trade.survived]
    symbols = sorted({trade.symbol for trade in trades})

    return {
        "entries": len(trades),
        "survivors": len(survivors),
        "survival_rate": round(len(survivors) / len(trades), 4),
        "median_entry_apr": round(median(trade.entry_apr for trade in trades), 4),
        "median_exit_apr": round(median(trade.exit_apr for trade in trades), 4),
        "mean_exit_apr": round(mean(trade.exit_apr for trade in trades), 4),
        "symbols": {
            symbol: summarize_symbol([trade for trade in trades if trade.symbol == symbol])
            for symbol in symbols
        },
    }


def summarize_symbol(trades: list[SurvivalTrade]) -> dict:
    survivors = [trade for trade in trades if trade.survived]
    return {
        "entries": len(trades),
        "survivors": len(survivors),
        "survival_rate": round(len(survivors) / len(trades), 4),
        "median_exit_apr": round(median(trade.exit_apr for trade in trades), 4),
    }


def run(path: str | Path, table: str | None, threshold: float, horizon_days: int) -> dict:
    points = load_funding_history(path, table)
    trades = survival_trades(points, threshold, horizon_days)
    result = summarize(trades)
    result["input_rows"] = len(points)
    result["entry_threshold_apr"] = threshold
    result["horizon_days"] = horizon_days
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Funding APR survival backtest")
    parser.add_argument("history_path", help="CSV or SQLite funding history")
    parser.add_argument("--table", default=None, help="SQLite table name")
    parser.add_argument("--threshold", type=float, default=0.40, help="Entry/survival APR threshold")
    parser.add_argument("--horizon-days", type=int, default=30, help="Survival horizon")
    args = parser.parse_args()

    result = run(args.history_path, args.table, args.threshold, args.horizon_days)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
