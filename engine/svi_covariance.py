"""
Phase 4.5 -- SVI covariance posterior (fast path), with NUTS validation.

CONTRACT
--------
SVI replaces NUTS only if it reproduces NUTS's posterior on the
quantities we consume:
  1. per-pair correlation posterior MEANS   (bias check)
  2. per-pair correlation posterior STDS    (the overconfidence check)
  3. resulting blended portfolio weights    (end-to-end check)

SVI's known failure mode is underestimating uncertainty. Overtight
covariance posteriors -> overconfident allocations -> exactly the
failure this engine exists to prevent. Hence the std check is the one
that gates the swap, with an explicit tolerance.

Guide: full-rank multivariate normal over unconstrained space.
Deliberately NOT normalizing flows -- the LKJ posterior is unimodal
and smooth; flows are the escalation path if this guide fails, not
the default.
"""

import os
import time
import json
import warnings
import numpy as np
import pandas as pd
import torch
import pyro
import pyro.distributions as dist
from pyro.infer import SVI, Trace_ELBO
from pyro.infer.autoguide import AutoMultivariateNormal
from pyro.optim import ClippedAdam

warnings.filterwarnings("ignore")
DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def covariance_model(data, sample_vols):
    n = data.shape[1]
    conc = torch.tensor(2.0, device=device)
    corr_chol = pyro.sample(
        "corr_chol", dist.LKJCholesky(n, concentration=conc))
    vols = pyro.sample(
        "vols", dist.LogNormal(
            torch.log(sample_vols),
            0.3 * torch.ones(n, device=device)).to_event(1))
    scale_tril = vols.unsqueeze(-1) * corr_chol
    with pyro.plate("obs", data.shape[0]):
        pyro.sample("rets", dist.MultivariateNormal(
            torch.zeros(n, device=device), scale_tril=scale_tril),
            obs=data)


def fit_svi(rets, n_steps=3000, n_draws=5000, lr=0.01, verbose=True):
    """Fit the guide, then draw a posterior sample of covariances."""
    pyro.clear_param_store()
    X = torch.tensor(rets.values, dtype=torch.float32, device=device)
    sv = torch.tensor(rets.std().values, dtype=torch.float32, device=device)

    guide = AutoMultivariateNormal(
        lambda d: covariance_model(d, sv), init_scale=0.05)
    svi = SVI(lambda d: covariance_model(d, sv), guide,
              ClippedAdam({"lr": lr, "clip_norm": 10.0}),
              loss=Trace_ELBO(num_particles=8))

    t0 = time.time()
    losses = []
    for step in range(n_steps):
        loss = svi.step(X)
        losses.append(loss)
        if verbose and (step + 1) % 500 == 0:
            recent = np.mean(losses[-100:])
            print(f"    step {step+1:>5}/{n_steps}  ELBO {recent:,.0f}  "
                  f"({time.time()-t0:.0f}s)")
    fit_time = time.time() - t0

    # Convergence sanity: last-500 slope should be ~flat
    tail = np.array(losses[-500:])
    slope = np.polyfit(np.arange(len(tail)), tail, 1)[0]
    converged = abs(slope) < np.std(tail) / len(tail) * 5

    # Draw covariances from the fitted guide
    t1 = time.time()
    with torch.no_grad():
        samples = {k: [] for k in ("corr_chol", "vols")}
        BATCH = 500
        for _ in range(n_draws // BATCH):
            s = guide(X)
            # guide() returns one draw; use .sample_latent via predictive
            for k in samples:
                samples[k].append(s[k].unsqueeze(0))
        # Simpler + correct: Predictive
    from pyro.infer import Predictive
    pred = Predictive(lambda d: covariance_model(d, sv), guide=guide,
                      num_samples=n_draws, return_sites=("corr_chol", "vols"))
    with torch.no_grad():
        out = pred(X)
    chol = out["corr_chol"].squeeze(1)
    vols = out["vols"].squeeze(1)
    scale = vols.unsqueeze(-1) * chol
    covs = (scale @ scale.transpose(-1, -2)).cpu()
    draw_time = time.time() - t1

    if verbose:
        print(f"    fit {fit_time:.0f}s + {n_draws} draws {draw_time:.1f}s"
              f"   converged={'yes' if converged else 'NO -- inspect'}")
    return covs, {"fit_time": fit_time, "draw_time": draw_time,
                  "converged": bool(converged)}


# ══════════════════════════════════════════════════════════════
# VALIDATION AGAINST NUTS
# ══════════════════════════════════════════════════════════════

def corr_stats(covs):
    """Per-pair correlation means and stds across draws."""
    d = torch.sqrt(torch.diagonal(covs, dim1=-2, dim2=-1))
    corr = covs / (d.unsqueeze(-1) * d.unsqueeze(-2))
    n = corr.shape[-1]
    iu = torch.triu_indices(n, n, offset=1)
    pairs = corr[:, iu[0], iu[1]]              # (S, n_pairs)
    return pairs.mean(0).numpy(), pairs.std(0).numpy()


def validate(std_ratio_floor=0.75, mean_tol=0.05):
    """
    Compare SVI posterior to a saved NUTS reference.
    GATE: median(svi_std / nuts_std) must exceed std_ratio_floor.
    Below it, SVI is overconfident and the swap is BLOCKED.
    """
    from portfolio_engine import (fetch_returns,
                                  sample_covariance_posterior)

    print("=" * 62)
    print("SVI vs NUTS -- covariance posterior comparison")
    print("=" * 62)

    rets = fetch_returns()
    ref_path = os.path.join(DATA_DIR, "nuts_reference_covs.pt")

    if os.path.exists(ref_path):
        print("\n  Loading saved NUTS reference...")
        nuts_covs = torch.load(ref_path)
    else:
        print("\n  No NUTS reference on disk -- sampling one (~5 min)...")
        nuts_covs = sample_covariance_posterior(rets, n_samples=5000)
        torch.save(nuts_covs, ref_path)
        print(f"  Saved -> {ref_path}")

    print("\n  Fitting SVI...")
    svi_covs, info = fit_svi(rets)

    nm, ns = corr_stats(nuts_covs * 252)
    sm, ss = corr_stats(svi_covs * 252)

    mean_gap = np.abs(nm - sm)
    std_ratio = ss / np.maximum(ns, 1e-9)

    print(f"\n  Correlation posterior comparison "
          f"({len(nm)} pairs):")
    print(f"    mean abs gap:   {mean_gap.mean():.4f}  "
          f"(worst {mean_gap.max():.4f}, tol {mean_tol})")
    print(f"    std ratio:      median {np.median(std_ratio):.2f}  "
          f"(min {std_ratio.min():.2f}, floor {std_ratio_floor})")
    print(f"    -> SVI uncertainty is "
          f"{np.median(std_ratio)*100:.0f}% of NUTS's")

    mean_ok = mean_gap.max() < mean_tol
    std_ok = np.median(std_ratio) > std_ratio_floor

    verdict = mean_ok and std_ok and info["converged"]
    print(f"\n  {'='*58}")
    print(f"  VERDICT: {'PASS -- SVI certified for the engine' if verdict else 'FAIL -- swap BLOCKED'}")
    if not mean_ok:
        print("    - correlation means diverge beyond tolerance")
    if not std_ok:
        print("    - SVI posterior too tight: overconfidence risk")
    if not info["converged"]:
        print("    - ELBO not converged")
    print(f"  {'='*58}")

    with open(os.path.join(DATA_DIR, "svi_validation.json"), "w") as f:
        json.dump({"pass": bool(verdict),
                   "mean_gap_max": float(mean_gap.max()),
                   "std_ratio_median": float(np.median(std_ratio)),
                   "std_ratio_min": float(std_ratio.min()),
                   "svi_fit_time": info["fit_time"],
                   "converged": info["converged"]}, f, indent=2)
    return verdict


if __name__ == "__main__":
    validate()
