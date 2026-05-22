import argparse
import json

from backtester.funding_survival import run as run_funding_survival
from signal_engine.persistence import train_and_report as train_persistence_classifier
from .funding_model import rank_opportunities
from .models import AccountConfig
from .sample_data import SAMPLE_OPPORTUNITIES


def sample() -> None:
    ranked = rank_opportunities(AccountConfig(), SAMPLE_OPPORTUNITIES)
    print(json.dumps(ranked, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Arbitrage research toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("sample")

    survival = subparsers.add_parser("funding-survival")
    survival.add_argument("history_path")
    survival.add_argument("--table", default=None)
    survival.add_argument("--threshold", type=float, default=0.40)
    survival.add_argument("--horizon-days", type=int, default=30)

    persistence = subparsers.add_parser("persistence")
    persistence.add_argument("features_path")
    persistence.add_argument("--holdout", type=float, default=None)
    persistence.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    if args.command == "sample":
        sample()
    elif args.command == "funding-survival":
        result = run_funding_survival(
            args.history_path,
            table=args.table,
            threshold=args.threshold,
            horizon_days=args.horizon_days,
        )
        print(json.dumps(result, indent=2))
    elif args.command == "persistence":
        result = train_persistence_classifier(
            args.features_path,
            holdout=args.holdout,
            seed=args.seed,
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
