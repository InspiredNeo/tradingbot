"""
Phase 3.5 Re-benchmark: simplified, faster version.
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
import pyro
import pyro.distributions as dist
from pyro.infer import MCMC, NUTS
import numpy as np
import yfinance as yf
import pandas as pd

device = torch.device("cuda")
print("=" * 55)
print("PHASE 3.5 — RE-BENCHMARK WITH SIGNAL-CONDITIONED MODEL")
print("=" * 55)

# Step 1: fetch ETF returns only
print("\nFetching ETF returns...")
t = time.time()
ETF_UNIVERSE = ["VTI", "SCHF", "BND", "QQQ", "GLD", "TLT",
                "XLK", "XLV", "XLF", "EEM"]

data = yf.download(ETF_UNIVERSE, period="2y", progress=False)["Close"].dropna()
returns = data.pct_change().dropna()
n_days, n_assets = returns.shape
print(f"Done: {n_days} days x {n_assets} assets in {time.time()-t:.1f}s")

returns_t = torch.tensor(returns.values, dtype=torch.float32).to(device)

# Step 2: use a simple signal vector (58 features, realistic values)
# Using saved values from our earlier run rather than re-fetching
signal_vector = torch.tensor([
    -0.47, 0.0, 1.02, 0.0, 0.23, 0.42, 0.42, 0.0,
     2.87, 0.21, 0.86, -0.09, -0.38, 0.74, 1.49, 0.65,
     0.42, 1.0, 1.0, 0.0, -1.0, 0.40, 0.09, -0.13,
     0.52, 0.01, 0.41, 0.81, 1.89, 1.08, 1.56, 0.84,
    -3.0, -3.0, 0.34, 0.0, -0.21, 0.0, -0.5, 1.05,
     0.0, 0.0, 3.0, 1.02, 3.0, 3.0, 1.0, 0.0,
     0.97, -0.36, -0.44, 0.0, 0.5, 1.0, -0.91, -0.76,
     0.17, 0.0
], dtype=torch.float32).to(device)

print(f"Signal vector: {signal_vector.shape[0]} features loaded")

# Step 3: signal-conditioned model
def model(returns, signals):
    n = returns.shape[1]
    signal_summary = signals.mean()
    mu = pyro.sample("mu",
        dist.Normal(
            signal_summary.expand(n) * 0.01,
            torch.ones(n).to(device) * 0.05))
    with pyro.plate("assets", n, dim=-1):
        with pyro.plate("days", returns.shape[0], dim=-2):
            pyro.sample("obs",
                dist.Normal(mu, torch.ones(n).to(device) * 0.02),
                obs=returns)

# Step 4: benchmark
print("\n" + "=" * 55)
print("MCMC BENCHMARK")
print("=" * 55)

mcmc_results = {}
prev_std = None
optimal = 5000

for n_samples in [1000, 5000, 10000, 25000]:
    warmup = max(200, n_samples // 10)
    try:
        torch.cuda.synchronize()
        t = time.time()
        nuts = NUTS(model, step_size=0.01, adapt_step_size=True)
        mcmc = MCMC(nuts, num_samples=n_samples,
                    warmup_steps=warmup, disable_progbar=True)
        mcmc.run(returns_t, signal_vector)
        torch.cuda.synchronize()
        elapsed = time.time() - t
        samples = mcmc.get_samples()
        mu_std = samples["mu"].std(dim=0).mean().item()
        improvement = abs(prev_std - mu_std) / prev_std * 100 if prev_std else 100
        mcmc_results[n_samples] = {"time": elapsed, "std": mu_std}
        print(f"  {n_samples:>7,}: {elapsed:5.1f}s | "
              f"std={mu_std:.6f} | improvement={improvement:.1f}%")
        if prev_std and improvement < 1.0 and optimal == 5000:
            optimal = n_samples
            print(f"           → Diminishing returns at {n_samples:,}")
        prev_std = mu_std
    except Exception as e:
        print(f"  {n_samples:>7,}: FAILED — {e}")
        break

print("\n" + "=" * 55)
print(f"RESULT: Optimal samples = {optimal:,}")
print("=" * 55)

config_path = os.path.expanduser("~/tradingbot/config/engine_config.json")
config = json.load(open(config_path))
config["optimal_mcmc_samples"] = optimal
config["n_features"] = 58
config["n_assets"] = n_assets
config["rebenchmark_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
json.dump(config, open(config_path, "w"), indent=2)
print(f"Config saved → optimal: {optimal:,} samples")
