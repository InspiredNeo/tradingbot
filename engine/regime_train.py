"""
Walk-forward evaluation of regime detection models.

VALIDATION DESIGN
-----------------
Labels for date D encode data through D+63 trading days. A random split
would put March 2009 in train and April 2009 in test -- the model would
interpolate between near-identical points and report inflated accuracy.

We use expanding-window walk-forward with a 68-day embargo:

  |-------- train --------|  embargo  |--- test ---|
                             68 days

Each fold trains only on the past and tests only on the future, with a
gap wide enough that no test label was influenced by data visible during
training.

BASELINES (a model must beat these to be worth using)
  1. Majority class      -- always predict Neutral, 54.2%
  2. VIX threshold       -- the dumb rule this project might not beat
  3. Logistic regression -- small, regularized, few features

With ~82 effective independent observations, a 23,880-parameter network
is expected to overfit. That is the hypothesis being tested.
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import balanced_accuracy_score, confusion_matrix

warnings.filterwarnings("ignore")
DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

REGIME_NAMES = ["Expansion", "Neutral", "Stress", "Crisis"]
EMBARGO_MONTHS = 4          # 68 trading days, on monthly samples
MIN_TRAIN = 60              # need at least 5 years before first test


def load_data():
    X = pd.read_parquet(os.path.join(DATA_DIR, "X_labeled.parquet"))
    y = pd.read_parquet(os.path.join(DATA_DIR, "y_labeled.parquet"))
    return X, y["label"].astype(int)


def walk_forward_splits(n, min_train=MIN_TRAIN, embargo=EMBARGO_MONTHS,
                        test_size=12):
    """
    Expanding-window splits with embargo.
    Yields (train_idx, test_idx) as integer positions.
    """
    start = min_train
    while start + embargo + test_size <= n:
        train_idx = np.arange(0, start)
        test_start = start + embargo
        test_idx = np.arange(test_start, min(test_start + test_size, n))
        if len(test_idx) > 0:
            yield train_idx, test_idx
        start += test_size


# ══════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════

def fit_majority(Xtr, ytr, Xte):
    """Baseline 1: always predict the most common training class."""
    return np.full(len(Xte), np.bincount(ytr).argmax())


def fit_vix_rule(Xtr, ytr, Xte, feat_names):
    """
    Baseline 2: the dumb rule. Threshold on realized vol, which is the
    single most informative feature by construction of the labels.
    Thresholds fit on the training fold only.
    """
    vi = feat_names.index("spy_realized_vol_63")
    vtr, vte = Xtr[:, vi], Xte[:, vi]
    # Fit thresholds as training-set quantiles
    q85, q95 = np.quantile(vtr, 0.85), np.quantile(vtr, 0.95)
    q50 = np.quantile(vtr, 0.50)
    preds = np.empty(len(vte), dtype=int)
    for i, v in enumerate(vte):
        if v >= q95:
            preds[i] = 3
        elif v >= q85:
            preds[i] = 2
        elif v < q50:
            preds[i] = 0
        else:
            preds[i] = 1
    return preds


def fit_logistic(Xtr, ytr, Xte, C=0.1):
    """Baseline 3: L2-regularized multinomial logistic regression."""
    sc = RobustScaler().fit(Xtr)
    clf = LogisticRegression(
        C=C, max_iter=5000, class_weight="balanced", random_state=0)
    clf.fit(sc.transform(Xtr), ytr)
    return clf.predict(sc.transform(Xte))


def fit_logistic_subset(Xtr, ytr, Xte, feat_names, C=0.5):
    """
    Simplest defensible model: logistic on four features chosen a priori
    for economic reasons, not by search. Volatility, credit stress,
    trailing momentum, and the yield curve.
    """
    keep = ["spy_realized_vol_63", "credit_z_252",
            "spy_mom_63", "spread_2_10"]
    ix = [feat_names.index(k) for k in keep if k in feat_names]
    sc = RobustScaler().fit(Xtr[:, ix])
    clf = LogisticRegression(C=C, max_iter=5000,
                             class_weight="balanced", random_state=0)
    clf.fit(sc.transform(Xtr[:, ix]), ytr)
    return clf.predict(sc.transform(Xte[:, ix]))


class TinyNet(nn.Module):
    """~600 params. Sized for ~82 effective observations."""
    def __init__(self, n_in, n_out=4, hidden=16):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_in, hidden), nn.LayerNorm(hidden), nn.GELU(),
            nn.Dropout(0.4), nn.Linear(hidden, n_out))

    def forward(self, x):
        return self.net(x)


class BigNet(nn.Module):
    """The original architecture: ~23,880 params. Expected to overfit."""
    def __init__(self, n_in, n_out=4):
        super().__init__()
        self.enc = nn.Sequential(
            nn.Linear(n_in, 128), nn.LayerNorm(128), nn.GELU(), nn.Dropout(0.2),
            nn.Linear(128, 64), nn.LayerNorm(64), nn.GELU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.LayerNorm(32), nn.GELU())
        self.att = nn.MultiheadAttention(32, 4, dropout=0.2, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(32, 32), nn.GELU(), nn.Dropout(0.2), nn.Linear(32, n_out))

    def forward(self, x):
        e = self.enc(x)
        a, _ = self.att(e.unsqueeze(1), e.unsqueeze(1), e.unsqueeze(1))
        return self.head(e + a.squeeze(1))


def fit_torch(model_cls, Xtr, ytr, Xte, epochs=300, lr=3e-3, seed=0):
    torch.manual_seed(seed)
    sc = RobustScaler().fit(Xtr)
    xtr = torch.tensor(sc.transform(Xtr), dtype=torch.float32).to(device)
    xte = torch.tensor(sc.transform(Xte), dtype=torch.float32).to(device)
    yt = torch.tensor(ytr, dtype=torch.long).to(device)

    model = model_cls(Xtr.shape[1]).to(device)
    # Class weights -- Crisis is 5% of the data
    counts = np.bincount(ytr, minlength=4).astype(float)
    w = torch.tensor(counts.sum() / (4 * np.maximum(counts, 1)),
                     dtype=torch.float32).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
    lossf = nn.CrossEntropyLoss(weight=w, label_smoothing=0.05)

    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        loss = lossf(model(xtr), yt)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

    model.eval()
    with torch.no_grad():
        train_acc = (model(xtr).argmax(1) == yt).float().mean().item()
        preds = model(xte).argmax(1).cpu().numpy()
    fit_torch.last_train_acc = train_acc
    return preds


# ══════════════════════════════════════════════════════════════
# EVALUATION
# ══════════════════════════════════════════════════════════════

def evaluate():
    X, y = load_data()
    feat_names = list(X.columns)
    Xv, yv = X.values, y.values
    n = len(Xv)

    splits = list(walk_forward_splits(n))
    print("=" * 68)
    print("WALK-FORWARD REGIME MODEL COMPARISON")
    print("=" * 68)
    print(f"\n  Samples: {n}   Features: {Xv.shape[1]}")
    print(f"  Folds: {len(splits)}   Embargo: {EMBARGO_MONTHS} months")
    print(f"  Test windows: {X.index[splits[0][1][0]].date()} -> "
          f"{X.index[splits[-1][1][-1]].date()}")

    models = {
        "Majority class":  lambda a, b, c: fit_majority(a, b, c),
        "Vol threshold":   lambda a, b, c: fit_vix_rule(a, b, c, feat_names),
        "Logistic (C=0.1)": lambda a, b, c: fit_logistic(a, b, c, C=0.1),
        "Logistic (C=1.0)": lambda a, b, c: fit_logistic(a, b, c, C=1.0),
        "Logistic 4-feat":  lambda a, b, c: fit_logistic_subset(
            a, b, c, feat_names),
        "TinyNet (~600p)": lambda a, b, c: fit_torch(
            TinyNet, a, b, c, epochs=1500, lr=1e-2),
        "BigNet (~24kp)":  lambda a, b, c: fit_torch(BigNet, a, b, c),
    }

    results = {k: {"pred": [], "true": []} for k in models}

    for fi, (tr, te) in enumerate(splits):
        Xtr, ytr = Xv[tr], yv[tr]
        Xte, yte = Xv[te], yv[te]
        if len(np.unique(ytr)) < 2:
            continue
        for name, fn in models.items():
            try:
                p = fn(Xtr, ytr, Xte)
                results[name]["pred"].extend(p)
                results[name]["true"].extend(yte)
            except Exception as e:
                print(f"    fold {fi} {name}: {e}")

    print("\n" + "=" * 68)
    print("POOLED OUT-OF-SAMPLE RESULTS")
    print("=" * 68)
    print(f"\n  {'model':<20} {'accuracy':>10} {'balanced':>10} "
          f"{'vs major':>10}")
    print("  " + "-" * 52)

    summary = {}
    major_acc = None
    for name in models:
        t = np.array(results[name]["true"])
        p = np.array(results[name]["pred"])
        if len(t) == 0:
            continue
        acc = (t == p).mean()
        bal = balanced_accuracy_score(t, p)
        if name == "Majority class":
            major_acc = acc
        delta = (acc - major_acc) * 100 if major_acc is not None else 0
        summary[name] = {"accuracy": float(acc), "balanced": float(bal),
                         "n": int(len(t))}
        print(f"  {name:<20} {acc:>9.1%} {bal:>10.1%} {delta:>+9.1f}pp")

    # Confusion matrix for the best balanced-accuracy model
    best = max((k for k in summary if k != "Majority class"),
               key=lambda k: summary[k]["balanced"])
    t = np.array(results[best]["true"])
    p = np.array(results[best]["pred"])
    cm = confusion_matrix(t, p, labels=[0, 1, 2, 3])
    print(f"\n  Confusion matrix -- {best} (rows=true, cols=pred)")
    print(f"    {'':<12}" + "".join(f"{n[:6]:>8}" for n in REGIME_NAMES))
    for i, name in enumerate(REGIME_NAMES):
        print(f"    {name:<12}" + "".join(f"{cm[i][j]:>8}" for j in range(4)))

    # Crisis recall specifically -- the case that matters most
    print("\n  Crisis detection (12 samples, 2 independent events):")
    for name in models:
        t = np.array(results[name]["true"])
        p = np.array(results[name]["pred"])
        if len(t) == 0:
            continue
        mask = t == 3
        if mask.sum() == 0:
            print(f"    {name:<20} no crisis samples in test folds")
            continue
        rec = (p[mask] == 3).mean()
        print(f"    {name:<20} {rec:.0%} recall "
              f"({int((p[mask]==3).sum())}/{int(mask.sum())})")

    with open(os.path.join(DATA_DIR, "model_comparison.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 68)
    return summary


if __name__ == "__main__":
    evaluate()
