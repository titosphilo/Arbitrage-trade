from signal_engine.persistence import (
    PersistenceClassifier,
    PersistenceSample,
    row_to_sample,
    train_and_report,
    train_test_split,
)


def test_label_is_one_when_survival_rate_exceeds_70_percent():
    sticky = PersistenceSample("RAVEUSDT", 0.04, 90, 0.18, "sticky_coin", 0.71)
    weak = PersistenceSample("COINUSDT", 0.41, 9, -0.22, "stock_perp", 0.70)

    assert sticky.label == 1
    assert weak.label == 0


def test_row_to_sample_accepts_percent_survival_rate():
    sample = row_to_sample(
        {
            "symbol": "raveusdt",
            "rate_volatility": "4%",
            "consecutive_positive_periods": "90",
            "oi_change_rate": "18%",
            "coin_category": "sticky_coin",
            "survival_rate": "100%",
        }
    )

    assert sample.symbol == "RAVEUSDT"
    assert sample.rate_volatility == 0.04
    assert sample.oi_change_rate == 0.18
    assert sample.label == 1


def test_classifier_scores_sticky_profile_above_fragile_profile():
    samples = [
        PersistenceSample("RAVEUSDT", 0.04, 90, 0.18, "sticky_coin", 1.00),
        PersistenceSample("BASUSDT", 0.05, 84, 0.12, "sticky_coin", 1.00),
        PersistenceSample("COINUSDT", 0.41, 9, -0.22, "stock_perp", 0.26),
        PersistenceSample("AMZNUSDT", 0.20, 18, -0.04, "stock_perp", 0.49),
    ]
    classifier = PersistenceClassifier.fit(samples, iterations=500)

    sticky_probability = classifier.predict_probability(samples[0])
    fragile_probability = classifier.predict_probability(samples[2])

    assert sticky_probability > fragile_probability


def test_train_and_report_loads_feature_csv():
    report = train_and_report("data/sample_persistence_features.csv")

    assert report["samples"] == 6
    assert "model" in report
    assert len(report["predictions"]) == 6


def test_train_and_report_supports_holdout_validation():
    report = train_and_report("data/sample_persistence_features.csv", holdout=0.20, seed=7)

    assert report["samples"] == 5
    assert report["holdout"]["samples"] == 1
    assert "recall" in report["holdout"]


def test_train_test_split_is_deterministic():
    samples = [
        PersistenceSample(f"SYM{index}", 0.1, index, 0.0, "test", index / 10)
        for index in range(10)
    ]

    first_train, first_test = train_test_split(samples, test_size=0.20, seed=3)
    second_train, second_test = train_test_split(samples, test_size=0.20, seed=3)

    assert first_train == second_train
    assert first_test == second_test
    assert len(first_test) == 2
