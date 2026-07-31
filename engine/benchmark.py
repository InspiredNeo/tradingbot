"""
System benchmark for Market Terminal bot engine.
Finds optimal configuration for RTX 5070 + Ryzen 9700X + 32GB RAM.
"""
import time
import json
import numpy as np
import torch
import pyro
import pyro.distributions as dist
from pyro.infer import MCMC, NUTS
from concurrent.futures import ThreadPoolExecutor
import psutil
import os

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
results = {}

print("=" * 60)
print("MARKET TERMINAL — SYSTEM BENCHMARK")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
print(f"CPU: {psutil.cpu_count(logical=False)} cores / {psutil.cpu_count()} threads")
print(f"RAM: {psutil.virtual_memory().total / 1e9:.1f}GB")
print("=" * 60)


# ── 1. MCMC Sample Benchmark ──────────────────────────────────
print("\n[1/5] MCMC Sample Count Benchmark")
print("Finding optimal samples vs quality tradeoff...")

n_assets = 20  # realistic ETF portfolio size
n_days = 1260  # 5 years daily

# Generate realistic return data
torch.manual_seed(42)
returns = torch.randn(n_days, n_assets).to(device) * 0.01

def portfolio_model(returns):
    n = returns.shape[1]
    mu = pyro.sample("mu", dist.Normal(
        torch.zeros(n).to(device),
        torch.ones(n).to(device) * 0.1
    ))
    sigma = pyro.sample("sigma", dist.HalfNormal(
        torch.ones(n).to(device) * 0.2
    ))
    with pyro.plate("assets", n, dim=-1):
        with pyro.plate("days", returns.shape[0], dim=-2):
            pyro.sample("obs", dist.Normal(mu, sigma), obs=returns)

sample_counts = [1000, 5000, 10000, 25000, 50000, 100000, 250000]
mcmc_results = {}

for n_samples in sample_counts:
    warmup = max(200, n_samples // 10)
    try:
        torch.cuda.synchronize()
        t = time.time()
        nuts = NUTS(portfolio_model)
        mcmc = MCMC(nuts, num_samples=n_samples, warmup_steps=warmup,
                    disable_progbar=True)
        mcmc.run(returns)
        torch.cuda.synchronize()
        elapsed = time.time() - t
        samples = mcmc.get_samples()
        mu_std = samples["mu"].std(dim=0).mean().item()
        mcmc_results[n_samples] = {
            "time": elapsed,
            "samples_per_sec": n_samples / elapsed,
            "posterior_std": mu_std,
        }
        print(f"  {n_samples:>7,} samples: {elapsed:5.1f}s "
              f"({n_samples/elapsed:,.0f} samples/sec) "
              f"posterior_std={mu_std:.6f}")
    except Exception as e:
        print(f"  {n_samples:>7,} samples: FAILED — {e}")
        break

results["mcmc"] = mcmc_results

# Find diminishing returns point
prev_std = None
optimal_samples = 10000
for n, r in mcmc_results.items():
    if prev_std is not None:
        improvement = abs(prev_std - r["posterior_std"]) / prev_std
        if improvement < 0.01:  # less than 1% improvement
            optimal_samples = n
            print(f"\n  → Diminishing returns after {n:,} samples "
                  f"(< 1% posterior improvement)")
            break
    prev_std = r["posterior_std"]

results["optimal_mcmc_samples"] = optimal_samples


# ── 2. Parallel Model Benchmark ───────────────────────────────
print("\n[2/5] Parallel Model Benchmark")
print("Finding optimal number of parallel models on GPU...")

def run_single_mcmc(model_id, n_samples=10000):
    torch.manual_seed(model_id)
    rets = torch.randn(252, 10).to(device) * 0.01
    def model(r):
        mu = pyro.sample(f"mu_{model_id}",
                         dist.Normal(torch.zeros(10).to(device),
                                    torch.ones(10).to(device)))
        with pyro.plate(f"assets_{model_id}", 10, dim=-1):
            with pyro.plate(f"d_{model_id}", r.shape[0], dim=-2):
                pyro.sample(f"obs_{model_id}", dist.Normal(mu, torch.ones(10).to(device)), obs=r)
    nuts = NUTS(model)
    mcmc = MCMC(nuts, num_samples=n_samples, warmup_steps=200, disable_progbar=True)
    mcmc.run(rets)
    return model_id

parallel_results = {}
for n_parallel in [1, 2, 3, 4, 6]:
    try:
        torch.cuda.synchronize()
        t = time.time()
        with ThreadPoolExecutor(max_workers=n_parallel) as ex:
            list(ex.map(run_single_mcmc, range(n_parallel)))
        torch.cuda.synchronize()
        elapsed = time.time() - t
        parallel_results[n_parallel] = elapsed
        efficiency = (parallel_results[1] * n_parallel) / elapsed if 1 in parallel_results else 1
        print(f"  {n_parallel} parallel models: {elapsed:.1f}s "
              f"(efficiency: {efficiency:.1%})")
    except Exception as e:
        print(f"  {n_parallel} parallel: FAILED — {e}")
        break

results["parallel"] = parallel_results

# Find optimal parallel count
best_parallel = min(parallel_results, key=parallel_results.get) if parallel_results else 1
results["optimal_parallel_models"] = best_parallel
print(f"\n  → Optimal parallel models: {best_parallel}")


# ── 3. CPU Thread Benchmark ───────────────────────────────────
print("\n[3/5] CPU Thread Benchmark")
print("Finding optimal thread count for data fetching...")

def fake_fetch(sym):
    time.sleep(0.1)  # simulate API call
    return np.random.randn(252)

symbols = [f"ETF_{i}" for i in range(50)]
thread_results = {}

for n_threads in [1, 2, 4, 8, 12, 16, 20]:
    t = time.time()
    with ThreadPoolExecutor(max_workers=n_threads) as ex:
        list(ex.map(fake_fetch, symbols))
    elapsed = time.time() - t
    thread_results[n_threads] = elapsed
    print(f"  {n_threads:>2} threads: {elapsed:.2f}s for 50 symbols")

results["threads"] = thread_results
optimal_threads = min(thread_results, key=thread_results.get)
results["optimal_threads"] = optimal_threads
print(f"\n  → Optimal fetch threads: {optimal_threads}")


# ── 4. VRAM Usage Benchmark ───────────────────────────────────
print("\n[4/5] VRAM Usage Benchmark")
print("Measuring VRAM per model to plan parallel capacity...")

vram_results = {}
for n_assets in [10, 20, 50, 100]:
    torch.cuda.empty_cache()
    before = torch.cuda.memory_allocated()
    rets = torch.randn(1260, n_assets).to(device)
    after = torch.cuda.memory_allocated()
    vram_mb = (after - before) / 1e6
    vram_results[n_assets] = vram_mb
    print(f"  {n_assets:>3} assets: {vram_mb:.1f}MB VRAM")
    del rets

total_vram = torch.cuda.get_device_properties(0).total_memory / 1e6
results["vram"] = vram_results
results["total_vram_mb"] = total_vram

# Calculate how many models fit in VRAM
model_vram = vram_results.get(20, 50) * 10  # rough estimate per model
max_models = int(total_vram * 0.8 / model_vram)  # use 80% VRAM
results["max_parallel_models"] = max_models
print(f"\n  → Can fit ~{max_models} models simultaneously in VRAM "
      f"(using 80% of {total_vram/1024:.1f}GB)")


# ── 5. Full Pipeline Benchmark ────────────────────────────────
print("\n[5/5] Full Pipeline Simulation")
print("Simulating complete bot cycle with optimal settings...")

n_samples = results.get("optimal_mcmc_samples", 10000)
n_threads = results.get("optimal_threads", 8)
n_models = min(results.get("optimal_parallel_models", 3), 6)

print(f"  Config: {n_samples:,} samples, {n_threads} threads, {n_models} parallel models")

stages = {}

# Signal collection
t = time.time()
with ThreadPoolExecutor(max_workers=n_threads) as ex:
    list(ex.map(fake_fetch, symbols[:30]))
stages["signal_collection"] = time.time() - t

# Regime detection (simulate small NN)
t = time.time()
net = torch.nn.Sequential(
    torch.nn.Linear(30, 128), torch.nn.ReLU(),
    torch.nn.Linear(128, 64), torch.nn.ReLU(),
    torch.nn.Linear(64, 8), torch.nn.Softmax(dim=-1)
).to(device)
x = torch.randn(1, 30).to(device)
for _ in range(100):  # simulate 100 inferences
    _ = net(x)
torch.cuda.synchronize()
stages["regime_detection"] = time.time() - t

# MCMC (single model)
t = time.time()
rets = torch.randn(252, 20).to(device) * 0.01
nuts = NUTS(portfolio_model)
mcmc = MCMC(nuts, num_samples=n_samples, warmup_steps=200, disable_progbar=True)
mcmc.run(rets)
torch.cuda.synchronize()
stages["mcmc_single"] = time.time() - t
stages["mcmc_all_models"] = stages["mcmc_single"] * n_models / n_models  # parallel

# Portfolio math
t = time.time()
cov = np.cov(np.random.randn(252, 20).T)
np.linalg.inv(cov)
np.linalg.eig(cov)
stages["portfolio_math"] = time.time() - t

# Stress testing
t = time.time()
scenarios = np.random.randn(5, 252, 20) * 0.02
for s in scenarios:
    np.cumprod(1 + s, axis=0).min()
stages["stress_test"] = time.time() - t

total = sum(stages.values()) + stages["mcmc_single"] * (n_models - 1)
stages["total_estimated"] = total

print(f"\n  Stage breakdown:")
for stage, t in stages.items():
    if stage != "total_estimated":
        print(f"    {stage:<25} {t:.2f}s")
print(f"\n  → Estimated full cycle: {total:.1f}s")
print(f"  → Rebalance frequency headroom: "
      f"{'weekly ✓ monthly ✓ daily ✓' if total < 300 else 'weekly ✓ monthly ✓'}")


# ── Save Results ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("BENCHMARK COMPLETE — OPTIMAL CONFIGURATION:")
print("=" * 60)
print(f"  MCMC samples:        {results.get('optimal_mcmc_samples', 10000):,}")
print(f"  Parallel models:     {results.get('optimal_parallel_models', 3)}")
print(f"  Fetch threads:       {results.get('optimal_threads', 8)}")
print(f"  Est. cycle time:     {stages.get('total_estimated', 0):.1f}s")
print(f"  GPU utilization:     ~{min(100, results.get('optimal_parallel_models', 3) * 20)}%")

config_path = os.path.expanduser("~/tradingbot/config/engine_config.json")
with open(config_path, "w") as f:
    json.dump({
        "optimal_mcmc_samples": results.get("optimal_mcmc_samples", 10000),
        "optimal_parallel_models": results.get("optimal_parallel_models", 3),
        "optimal_fetch_threads": results.get("optimal_threads", 8),
        "estimated_cycle_time": stages.get("total_estimated", 0),
        "benchmark_date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, f, indent=2)
print(f"\n  Config saved to: {config_path}")
