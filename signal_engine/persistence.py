"""
Persistence Classifier — dependency-free logistic regression.

Predicts whether a coin's funding rate will stay positive for 30 days.
Label = 1 if survival_rate > 70%, 0 otherwise.

Features:
  - rate_volatility           : std of 8h funding rates (lower = more stable)
  - consecutive_positive_periods: longest run of positive periods
  - oi_change_rate            : OI trend proxy (positive = growing interest)
  - coin_category             : sticky_coin / stock_perp / major_crypto / niche_crypto

No scikit-learn required — pure numpy logistic regression.
"""

import csv, math, numpy as np
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "persistence_features.csv"

CATEGORY_ENCODE = {
    'sticky_coin':   [1, 0, 0, 0],
    'stock_perp':    [0, 1, 0, 0],
    'major_crypto':  [0, 0, 1, 0],
    'niche_crypto':  [0, 0, 0, 1],
}


def load_features(path=DATA_FILE) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Returns X (n_samples, n_features), y (n_samples,), symbols list."""
    X, y, syms = [], [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            vol     = float(row['rate_volatility'])
            consec  = float(row['consecutive_positive_periods'])
            oi_chg  = float(row['oi_change_rate'])
            cat     = row['coin_category']
            surv    = float(row['survival_rate'])
            label   = 1 if surv > 0.70 else 0
            cat_enc = CATEGORY_ENCODE.get(cat, [0, 0, 0, 1])
            X.append([vol, consec / 100.0, oi_chg] + cat_enc)
            y.append(label)
            syms.append(row['symbol'])
    return np.array(X), np.array(y), syms


def sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -500, 500)))


def train(X, y, lr=0.05, epochs=500) -> np.ndarray:
    """Train logistic regression with gradient descent."""
    n_feat = X.shape[1]
    w = np.zeros(n_feat + 1)          # weights + bias
    Xb = np.column_stack([np.ones(len(X)), X])
    for _ in range(epochs):
        pred = sigmoid(Xb @ w)
        grad = Xb.T @ (pred - y) / len(y)
        w   -= lr * grad
    return w


def predict_proba(X, w) -> np.ndarray:
    Xb = np.column_stack([np.ones(len(X)), X])
    return sigmoid(Xb @ w)


def evaluate(y_true, y_pred_proba, threshold=0.5) -> dict:
    y_pred = (y_pred_proba >= threshold).astype(int)
    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    acc = (tp + tn) / max(len(y_true), 1)
    prec = tp / max(tp + fp, 1)
    rec  = tp / max(tp + fn, 1)
    return dict(accuracy=round(acc,3), precision=round(prec,3),
                recall=round(rec,3), tp=tp, fp=fp, tn=tn, fn=fn)


def score_symbol(features: dict, w: np.ndarray) -> float:
    """Score a single coin: returns P(sticky)."""
    vol    = features.get('rate_volatility', 0.1)
    consec = features.get('consecutive_positive_periods', 0)
    oi_chg = features.get('oi_change_rate', 0)
    cat    = features.get('coin_category', 'niche_crypto')
    cat_enc = CATEGORY_ENCODE.get(cat, [0, 0, 0, 1])
    x = np.array([[vol, consec / 100.0, oi_chg] + cat_enc])
    return float(predict_proba(x, w)[0])


def run(path=DATA_FILE):
    X, y, syms = load_features(path)
    w = train(X, y)
    proba = predict_proba(X, w)
    metrics = evaluate(y, proba)

    feature_names = ['bias','vol','consec/100','oi_chg','sticky','stock','major','niche']
    print(f"\n  Persistence Classifier — logistic regression (no dependencies)")
    print(f"  Training samples: {len(y)} ({int(y.sum())} sticky, {int((1-y).sum())} unsticky)")
    print(f"\n  Accuracy:  {metrics['accuracy']*100:.1f}%")
    print(f"  Precision: {metrics['precision']*100:.1f}%  (of predicted sticky, how many are)")
    print(f"  Recall:    {metrics['recall']*100:.1f}%    (of actual sticky, how many found)")
    print(f"  TP={metrics['tp']} FP={metrics['fp']} TN={metrics['tn']} FN={metrics['fn']}")
    print(f"\n  Learned weights:")
    for name, wi in zip(feature_names, w):
        bar = '█' * int(abs(wi)*3) if abs(wi) < 10 else '█'*10
        sign = '+' if wi >= 0 else '-'
        print(f"  {name:12} {wi:>+7.3f}  {sign}{bar}")
    print(f"\n  Top sticky predictions:")
    ranked = sorted(zip(syms, proba, y), key=lambda x: -x[1])
    for sym, p, label in ranked[:10]:
        tag = '✅ sticky' if label==1 else '❌ unsticky'
        print(f"  {sym:22} P(sticky)={p:.3f}  actual={tag}")
    return w, metrics


if __name__ == '__main__':
    run()
