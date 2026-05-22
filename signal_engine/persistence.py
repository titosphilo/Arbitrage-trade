import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev


CATEGORY_COLUMNS = ("coin_category", "category", "sector", "type")
SYMBOL_COLUMNS = ("symbol", "pair", "ticker", "contract")
SURVIVAL_COLUMNS = ("survival_rate", "survival", "thirty_day_survival_rate")
VOLATILITY_COLUMNS = ("rate_volatility", "funding_rate_volatility", "apr_volatility")
STREAK_COLUMNS = (
    "consecutive_positive_periods",
    "positive_period_streak",
    "positive_funding_streak",
)
OI_CHANGE_COLUMNS = ("oi_change_rate", "open_interest_change_rate", "open_interest_delta")


@dataclass(frozen=True)
class PersistenceSample:
    symbol: str
    rate_volatility: float
    consecutive_positive_periods: float
    oi_change_rate: float
    coin_category: str
    survival_rate: float

    @property
    def label(self) -> int:
        return int(self.survival_rate > 0.70)


@dataclass(frozen=True)
class PersistencePrediction:
    symbol: str
    survival_probability: float
    predicted_label: int
    score: float


def first_present(row: dict, candidates: tuple[str, ...], default: object = None) -> object:
    for column in candidates:
        if column in row and row[column] not in (None, ""):
            return row[column]
    if default is not None:
        return default
    raise KeyError(f"missing one of: {', '.join(candidates)}")


def parse_float(value: object) -> float:
    text = str(value).strip().replace("%", "")
    number = float(text)
    if "%" in str(value):
        return number / 100
    return number


def row_to_sample(row: dict) -> PersistenceSample:
    return PersistenceSample(
        symbol=str(first_present(row, SYMBOL_COLUMNS)).strip().upper(),
        rate_volatility=parse_float(first_present(row, VOLATILITY_COLUMNS)),
        consecutive_positive_periods=parse_float(first_present(row, STREAK_COLUMNS)),
        oi_change_rate=parse_float(first_present(row, OI_CHANGE_COLUMNS)),
        coin_category=str(first_present(row, CATEGORY_COLUMNS, "unknown")).strip().lower(),
        survival_rate=parse_float(first_present(row, SURVIVAL_COLUMNS)),
    )


def load_samples(path: str | Path) -> list[PersistenceSample]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [row_to_sample(row) for row in reader]


class PersistenceClassifier:
    def __init__(
        self,
        weights: list[float],
        means: list[float],
        scales: list[float],
        categories: list[str],
    ) -> None:
        self.weights = weights
        self.means = means
        self.scales = scales
        self.categories = categories

    @classmethod
    def fit(
        cls,
        samples: list[PersistenceSample],
        *,
        iterations: int = 2_000,
        learning_rate: float = 0.08,
        l2: float = 0.01,
    ) -> "PersistenceClassifier":
        if not samples:
            raise ValueError("cannot fit persistence classifier with no samples")

        categories = sorted({sample.coin_category for sample in samples})
        raw_features = [feature_vector(sample, categories) for sample in samples]
        means, scales = feature_stats(raw_features)
        features = [standardize(vector, means, scales) for vector in raw_features]
        labels = [sample.label for sample in samples]
        weights = [0.0 for _ in range(len(features[0]) + 1)]

        for _ in range(iterations):
            gradients = [0.0 for _ in weights]
            for vector, label in zip(features, labels):
                predicted = sigmoid(weights[0] + dot(weights[1:], vector))
                error = predicted - label
                gradients[0] += error
                for index, value in enumerate(vector, start=1):
                    gradients[index] += error * value

            count = len(samples)
            weights[0] -= learning_rate * gradients[0] / count
            for index in range(1, len(weights)):
                regularized = gradients[index] / count + l2 * weights[index]
                weights[index] -= learning_rate * regularized

        return cls(weights=weights, means=means, scales=scales, categories=categories)

    def predict_probability(self, sample: PersistenceSample) -> float:
        vector = standardize(feature_vector(sample, self.categories), self.means, self.scales)
        return sigmoid(self.weights[0] + dot(self.weights[1:], vector))

    def predict(self, sample: PersistenceSample, threshold: float = 0.50) -> PersistencePrediction:
        probability = self.predict_probability(sample)
        return PersistencePrediction(
            symbol=sample.symbol,
            survival_probability=round(probability, 4),
            predicted_label=int(probability >= threshold),
            score=round((probability - 0.5) * 2, 4),
        )

    def to_dict(self) -> dict:
        return {
            "weights": self.weights,
            "means": self.means,
            "scales": self.scales,
            "categories": self.categories,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "PersistenceClassifier":
        return cls(
            weights=[float(value) for value in payload["weights"]],
            means=[float(value) for value in payload["means"]],
            scales=[float(value) for value in payload["scales"]],
            categories=[str(value) for value in payload["categories"]],
        )


def feature_vector(sample: PersistenceSample, categories: list[str]) -> list[float]:
    category_flags = [1.0 if sample.coin_category == category else 0.0 for category in categories]
    return [
        sample.rate_volatility,
        sample.consecutive_positive_periods,
        sample.oi_change_rate,
        *category_flags,
    ]


def feature_stats(vectors: list[list[float]]) -> tuple[list[float], list[float]]:
    columns = list(zip(*vectors))
    means = [mean(column) for column in columns]
    scales = [pstdev(column) or 1.0 for column in columns]
    return means, scales


def standardize(vector: list[float], means: list[float], scales: list[float]) -> list[float]:
    return [(value - center) / scale for value, center, scale in zip(vector, means, scales)]


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def evaluate(classifier: PersistenceClassifier, samples: list[PersistenceSample]) -> dict:
    predictions = [classifier.predict(sample) for sample in samples]
    labels = [sample.label for sample in samples]

    true_positive = sum(
        1 for prediction, label in zip(predictions, labels) if prediction.predicted_label == 1 and label == 1
    )
    true_negative = sum(
        1 for prediction, label in zip(predictions, labels) if prediction.predicted_label == 0 and label == 0
    )
    false_positive = sum(
        1 for prediction, label in zip(predictions, labels) if prediction.predicted_label == 1 and label == 0
    )
    false_negative = sum(
        1 for prediction, label in zip(predictions, labels) if prediction.predicted_label == 0 and label == 1
    )

    total = len(samples) or 1
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    return {
        "samples": len(samples),
        "positive_labels": sum(labels),
        "negative_labels": len(labels) - sum(labels),
        "accuracy": round((true_positive + true_negative) / total, 4),
        "precision": round(true_positive / precision_denominator, 4)
        if precision_denominator
        else 0.0,
        "recall": round(true_positive / recall_denominator, 4)
        if recall_denominator
        else 0.0,
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }


def train_test_split(
    samples: list[PersistenceSample],
    *,
    test_size: float = 0.20,
    seed: int = 42,
) -> tuple[list[PersistenceSample], list[PersistenceSample]]:
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    if len(samples) < 2:
        raise ValueError("at least two samples are required for holdout validation")

    shuffled = list(samples)
    random.Random(seed).shuffle(shuffled)
    test_count = max(1, round(len(shuffled) * test_size))
    test = shuffled[:test_count]
    train = shuffled[test_count:]
    if not train:
        raise ValueError("holdout split left no training samples")
    return train, test


def train_and_report(
    path: str | Path,
    *,
    holdout: float | None = None,
    seed: int = 42,
) -> dict:
    samples = load_samples(path)

    if holdout is None:
        train_samples = samples
        test_samples: list[PersistenceSample] = []
    else:
        train_samples, test_samples = train_test_split(samples, test_size=holdout, seed=seed)

    classifier = PersistenceClassifier.fit(train_samples)
    report = evaluate(classifier, train_samples)
    report["model"] = classifier.to_dict()
    report["predictions"] = [
        classifier.predict(sample).__dict__ | {"actual_label": sample.label}
        for sample in train_samples
    ]
    if test_samples:
        report["holdout"] = evaluate(classifier, test_samples)
        report["holdout"]["predictions"] = [
            classifier.predict(sample).__dict__ | {"actual_label": sample.label}
            for sample in test_samples
        ]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Train funding persistence classifier")
    parser.add_argument("features_path", help="CSV with survival_rate and persistence features")
    parser.add_argument("--holdout", type=float, default=None, help="Held-out test fraction")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic split seed")
    args = parser.parse_args()

    print(json.dumps(train_and_report(args.features_path, holdout=args.holdout, seed=args.seed), indent=2))


if __name__ == "__main__":
    main()
