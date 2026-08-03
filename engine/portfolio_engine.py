"""
Phase 5 -- Portfolio engine built on covariance uncertainty.

WHAT THIS DELIBERATELY DOES NOT DO
-----------------------------------
No component estimates expected returns. Walk-forward testing showed
return forecasting to be luck in our data (regime_train.py results),
so the engine only uses quantities that are persistent and estimable
from the present:

  - volatilities & correlations  (Bayesian posterior via MCMC on GPU)
  - market-cap equilibrium       (what current prices imply -- BL anchor
                                  without the views layer)
  - the stability dial           (present-tense risk scaling)

UNCERTAINTY INTEGRATION
-----------------------
Instead of: estimate covariance -> optimize once,
we do:      sample 5,000 plausible covariances -> optimize against
            each -> average the weights.

A position that's only attractive under ONE specific correlation
estimate gets shrunk automatically; positions robust across the whole
posterior survive. This is where the GPU earns its keep (5k samples
benchmarked at ~23s in engine_config.json).
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import torch
import yfinance as yf

warnings.filterwarnings("ignore")
DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
CONFIG = os.path.expanduser("~/tradingbot/config")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ── Universe: role matters for dial scaling ───────────────────
RISK_ASSETS = ["VTI", "SCHF", "QQQ", "EEM", "XLV", "XLF"]
DEFENSIVE   = ["AGG", "TLT", "GLD"]
UNIVERSE = RISK_ASSETS + DEFENSIVE

MAX_WEIGHT = 0.40          # hard cap, any single ETF
MCMC_SAMPLES = 5000        # from engine_config benchmark
LOOKBACK_DAYS = 504        # 2y daily for covariance estimation


# ══════════════════════════════════════════════════════════════
# DATA
# ══════════════════════════════════════════════════════════════

def fetch_returns(lookback=LOOKBACK_DAYS):
    px = yf.download(UNIVERSE, period="3y", progress=False,
                     auto_adjust=True)["Close"][UNIVERSE].dropna()
    rets = px.pct_change().dropna().iloc[-lookback:]
    return rets


def fetch_market_caps():
    """AUM proxies for the equilibrium anchor. Coarse is fine --
    the anchor only needs rough relative scale, and it's the one
    place 'what does the market currently believe' enters."""
    caps = {}
    for t in UNIVERSE:
        try:
            info = yf.Ticker(t).info
            caps[t] = info.get("totalAssets") or 1e9
        except Exception:
            caps[t] = 1e9
    w = pd.Series(caps)
    return w / w.sum()


# ══════════════════════════════════════════════════════════════
# BAYESIAN COVARIANCE -- the MCMC target
# ══════════════════════════════════════════════════════════════

def sample_covariance_posterior(rets, n_samples=MCMC_SAMPLES):
    """
    Posterior over the covariance matrix via Bayesian estimation:
      correlations ~ LKJ(concentration=2)   (mild prior toward sanity)
      vols         ~ LogNormal centered on sample vols
      returns      ~ MultivariateNormal(0, cov)

    Mean-zero likelihood is DELIBERATE: we refuse to estimate the mean
    (that's return forecasting). Slightly miss-specified, hugely more
    honest.

    Returns tensor of covariance draws: (n_samples, n, n)
    """
    import pyro
    import pyro.distributions as dist
    from pyro.infer import MCMC, NUTS

    pyro.clear_param_store()
    X = torch.tensor(rets.values, dtype=torch.float32, device=device)
    n = X.shape[1]
    sample_vols = torch.tensor(rets.std().values * np.sqrt(1.0),
                               dtype=torch.float32, device=device)

    def model(data):
        conc = torch.tensor(2.0, device=device)
        corr_chol = pyro.sample(
            "corr_chol", dist.LKJCholesky(n, concentration=conc))
        vols = pyro.sample(
            "vols", dist.LogNormal(
                torch.log(sample_vols), 0.3 * torch.ones(n, device=device)
            ).to_event(1))
        scale_tril = vols.unsqueeze(-1) * corr_chol
        with pyro.plate("obs", data.shape[0]):
            pyro.sample("rets", dist.MultivariateNormal(
                torch.zeros(n, device=device), scale_tril=scale_tril),
                obs=data)

    nuts = NUTS(model, target_accept_prob=0.8)
    mcmc = MCMC(nuts, num_samples=n_samples,
                warmup_steps=max(300, n_samples // 10),
                disable_progbar=False)   # visible progress: warmup + sampling
    mcmc.run(X)
    s = mcmc.get_samples()

    chol = s["corr_chol"]                       # (S, n, n)
    vols = s["vols"]                            # (S, n)
    scale = vols.unsqueeze(-1) * chol
    covs = scale @ scale.transpose(-1, -2)      # (S, n, n)
    return covs.cpu()


# ══════════════════════════════════════════════════════════════
# ALLOCATION MODELS -- all covariance-only
# ══════════════════════════════════════════════════════════════

def _project_simplex_capped(w, cap=MAX_WEIGHT):
    """Clip to [0, cap], renormalize, iterate to respect the cap."""
    w = np.clip(w, 0, None)
    for _ in range(20):
        w = w / w.sum()
        over = w > cap
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        under = ~over
        if under.any():
            w[under] += excess * (w[under] / w[under].sum())
    return w / w.sum()


def min_variance(cov):
    n = cov.shape[0]
    try:
        inv = np.linalg.pinv(cov)
        w = inv @ np.ones(n)
        return _project_simplex_capped(w)
    except np.linalg.LinAlgError:
        return np.ones(n) / n


def risk_parity(cov, iters=200):
    """Equal risk contribution via multiplicative updates."""
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(iters):
        rc = w * (cov @ w)
        target = rc.mean()
        w = w * (target / np.maximum(rc, 1e-12)) ** 0.3
        w = w / w.sum()
    return _project_simplex_capped(w)


def max_diversification(cov):
    """Maximize weighted-avg-vol / portfolio-vol."""
    vols = np.sqrt(np.diag(cov))
    try:
        inv = np.linalg.pinv(cov)
        w = inv @ vols
        return _project_simplex_capped(w)
    except np.linalg.LinAlgError:
        return np.ones(len(vols)) / len(vols)


def equal_weight(cov):
    n = cov.shape[0]
    return np.ones(n) / n


def bl_equilibrium(cov, market_w):
    """The BL anchor: market-cap weights, capped. No views, no forecast
    -- purely 'what does the market currently hold'."""
    return _project_simplex_capped(market_w.copy())


MODELS = {
    "risk_parity":     risk_parity,
    "min_variance":    min_variance,
    "max_divers":      max_diversification,
    "equal_weight":    equal_weight,
    "bl_equilibrium":  None,   # handled separately (needs market caps)
}

# Fixed a-priori blend -- same philosophy as the dial. Risk parity
# leads because it degrades most gracefully under covariance error.
MODEL_BLEND = {
    "risk_parity":    0.35,
    "min_variance":   0.20,
    "max_divers":     0.15,
    "equal_weight":   0.15,
    "bl_equilibrium": 0.15,
}


# ══════════════════════════════════════════════════════════════
# ENGINE
# ══════════════════════════════════════════════════════════════

def compute_allocation(dial_value=None, n_cov_draws=400, verbose=True,
                       n_samples=MCMC_SAMPLES, method="svi"):
    """
    Full pipeline:
      1. Posterior covariance draws (subsample for the optimizer loop)
      2. Solve each model against each draw, average -> per-model weights
      3. Blend models (fixed weights)
      4. Dial scales risk sleeve vs defensive sleeve
    """
    if verbose:
        print("=" * 60)
        print("PORTFOLIO ENGINE -- covariance-uncertainty allocation")
        print("=" * 60)

    rets = fetch_returns()
    market_w = fetch_market_caps()[UNIVERSE].values
    if verbose:
        print(f"\n  Universe: {len(UNIVERSE)} ETFs, "
              f"{len(rets)} days of returns")
        print(f"  Sampling covariance posterior "
              f"({MCMC_SAMPLES} draws on {device})...")

    if method == "svi":
        from svi_covariance import fit_svi
        covs, _ = fit_svi(rets, n_draws=n_samples, verbose=verbose)
    else:
        covs = sample_covariance_posterior(rets, n_samples=n_samples)
    # Optimizing against all 5k draws is wasteful; a spread of 400
    # captures the posterior. Thin evenly.
    idx = np.linspace(0, covs.shape[0] - 1, n_cov_draws).astype(int)
    covs_np = covs[idx].numpy() * 252     # annualize

    if verbose:
        avg_corr = np.corrcoef(rets.values.T)
        offdiag = avg_corr[np.triu_indices_from(avg_corr, k=1)]
        print(f"  Posterior: {n_cov_draws} draws used for optimization")
        print(f"  Sample avg pairwise correlation: {offdiag.mean():.2f}")

    # -- per-model weights, averaged over the posterior --
    per_model = {}
    for name, fn in MODELS.items():
        if name == "bl_equilibrium":
            per_model[name] = bl_equilibrium(covs_np.mean(0), market_w)
            continue
        ws = np.stack([fn(c) for c in covs_np])
        per_model[name] = ws.mean(axis=0)

    # -- blend --
    w = sum(per_model[m] * MODEL_BLEND[m] for m in MODEL_BLEND)
    w = _project_simplex_capped(w)

    # -- risk tolerance: baseline sleeve split (WHO YOU ARE) --
    # Applied before the dial (HOW DANGEROUS NOW IS). Tolerance sets
    # the calm-market portfolio; the dial scales away from it.
    RISK_TARGETS = {1: 0.35, 2: 0.50, 3: 0.62, 4: 0.75, 5: 0.88}
    try:
        bot_cfg = json.load(open(os.path.join(CONFIG, "bot_config.json")))
        tolerance = int(bot_cfg.get("risk_tolerance", 3))
    except Exception:
        tolerance = 3
    tolerance = max(1, min(5, tolerance))
    target_risk = RISK_TARGETS[tolerance]

    risk_ix_ = [UNIVERSE.index(t) for t in RISK_ASSETS]
    def_ix_ = [UNIVERSE.index(t) for t in DEFENSIVE]
    cur_risk = w[risk_ix_].sum()
    if cur_risk > 0 and cur_risk < 1:
        w[risk_ix_] *= target_risk / cur_risk
        w[def_ix_] *= (1 - target_risk) / (1 - cur_risk)
        w = w / w.sum()

    # -- dial scaling --
    if dial_value is None:
        stab = pd.read_parquet(os.path.join(DATA_DIR, "stability.parquet"))
        dial_value = float(stab["stability_risk"].dropna().iloc[-1])
    from stability_index import risk_multiplier
    mult = risk_multiplier(dial_value)

    w_final = w.copy()
    risk_ix = [UNIVERSE.index(t) for t in RISK_ASSETS]
    def_ix = [UNIVERSE.index(t) for t in DEFENSIVE]
    freed = w_final[risk_ix].sum() * (1 - mult)
    w_final[risk_ix] *= mult
    w_final[def_ix] += freed * (w_final[def_ix] / w_final[def_ix].sum())
    w_final = w_final / w_final.sum()

    result = {
        "weights": {t: round(float(x), 4)
                    for t, x in zip(UNIVERSE, w_final)},
        "pre_dial_weights": {t: round(float(x), 4)
                             for t, x in zip(UNIVERSE, w)},
        "per_model": {m: {t: round(float(x), 4)
                          for t, x in zip(UNIVERSE, v)}
                      for m, v in per_model.items()},
        "risk_tolerance": tolerance,
        "baseline_risk_target": target_risk,
        "dial": round(dial_value, 3),
        "risk_multiplier": round(mult, 3),
        "risk_sleeve": round(float(w_final[risk_ix].sum()), 3),
        "defensive_sleeve": round(float(w_final[def_ix].sum()), 3),
        "timestamp": pd.Timestamp.now().isoformat(),
    }

    with open(os.path.join(CONFIG, "target_allocation.json"), "w") as f:
        json.dump(result, f, indent=2)

    if verbose:
        print(f"\n  Risk tolerance: {tolerance}/5 -> baseline risk "
              f"sleeve {target_risk:.0%}")
        print(f"  Dial: {dial_value:.2f} -> risk multiplier {mult:.2f}")
        print(f"  Sleeves: risk {result['risk_sleeve']:.0%} / "
              f"defensive {result['defensive_sleeve']:.0%}")
        print(f"\n  {'ETF':<6} {'final':>8} {'pre-dial':>9}   role")
        for t in UNIVERSE:
            role = "risk" if t in RISK_ASSETS else "defensive"
            print(f"  {t:<6} {result['weights'][t]:>7.1%} "
                  f"{result['pre_dial_weights'][t]:>8.1%}   {role}")
        print(f"\n  Saved -> {CONFIG}/target_allocation.json")

    return result


if __name__ == "__main__":
    compute_allocation()
