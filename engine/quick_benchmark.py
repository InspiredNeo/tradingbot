import time, json, numpy as np, torch, pyro
import pyro.distributions as dist
from pyro.infer import MCMC, NUTS
from concurrent.futures import ThreadPoolExecutor
import psutil, os

device = torch.device("cuda")
print("=" * 50)
print("QUICK SYSTEM BENCHMARK")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB")
print(f"CPU: {psutil.cpu_count(logical=False)}c/{psutil.cpu_count()}t")
print(f"RAM: {psutil.virtual_memory().total/1e9:.1f}GB")
print("=" * 50)

returns = torch.randn(252, 20).to(device) * 0.01

def portfolio_model(returns):
    n = returns.shape[1]
    mu = pyro.sample("mu", dist.Normal(
        torch.zeros(n).to(device),
        torch.ones(n).to(device) * 0.1))
    with pyro.plate("assets", n, dim=-1):
        with pyro.plate("days", returns.shape[0], dim=-2):
            pyro.sample("obs", dist.Normal(mu,
                torch.ones(n).to(device) * 0.02), obs=returns)

# MCMC benchmark
print("\n[1/3] MCMC Sample Benchmark...")
mcmc_times = {}
prev_std = None
optimal = 10000
for n_samples in [1000, 5000, 10000, 25000, 50000, 100000]:
    t = time.time()
    nuts = NUTS(portfolio_model, step_size=0.01, adapt_step_size=True)
    mcmc = MCMC(nuts, num_samples=n_samples,
                warmup_steps=max(100, n_samples//10),
                disable_progbar=True)
    mcmc.run(returns)
    torch.cuda.synchronize()
    elapsed = time.time() - t
    std = mcmc.get_samples()["mu"].std(dim=0).mean().item()
    mcmc_times[n_samples] = elapsed
    improvement = abs(prev_std - std) / prev_std * 100 if prev_std else 100
    print(f"  {n_samples:>7,}: {elapsed:5.1f}s | std={std:.6f} | "
          f"improvement={improvement:.1f}%")
    if prev_std and improvement < 1.0 and optimal == 10000:
        optimal = n_samples
        print(f"           → Diminishing returns here")
    prev_std = std

print(f"\n  Optimal samples: {optimal:,}")

# Thread benchmark
print("\n[2/3] CPU Thread Benchmark...")
def fake_fetch(x): time.sleep(0.08); return np.random.randn(252)
thread_times = {}
for n in [4, 8, 12, 16]:
    t = time.time()
    with ThreadPoolExecutor(max_workers=n) as ex:
        list(ex.map(fake_fetch, range(50)))
    thread_times[n] = time.time() - t
    print(f"  {n:>2} threads: {thread_times[n]:.2f}s")
optimal_threads = min(thread_times, key=thread_times.get)

# VRAM benchmark
print("\n[3/3] VRAM Usage per Model...")
vram_total = torch.cuda.get_device_properties(0).total_memory / 1e9
models = []
for i in range(6):
    d = torch.randn(1260, 20).to(device)
    models.append(d)
    used = torch.cuda.memory_allocated() / 1e9
    print(f"  Model {i+1}: {used:.2f}GB / {vram_total:.1f}GB "
          f"({used/vram_total*100:.0f}%)")
for d in models: del d
torch.cuda.empty_cache()

# Save config
cycle = mcmc_times.get(optimal, 10) * 6 / 2 + 5
config = {
    "optimal_mcmc_samples": optimal,
    "optimal_parallel_models": 6,
    "optimal_fetch_threads": optimal_threads,
    "estimated_cycle_time_sec": round(cycle, 1),
    "mcmc_times": {str(k): round(v,2) for k,v in mcmc_times.items()},
}
path = os.path.expanduser("~/tradingbot/config/engine_config.json")
with open(path, "w") as f:
    json.dump(config, f, indent=2)

print("\n" + "=" * 50)
print("OPTIMAL CONFIGURATION:")
print(f"  MCMC samples:    {optimal:,}")
print(f"  Parallel models: 6")
print(f"  Fetch threads:   {optimal_threads}")
print(f"  Est cycle time:  ~{cycle:.0f}s")
print(f"  Config saved:    {path}")
