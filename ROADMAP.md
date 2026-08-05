# Market Terminal — Full Project Roadmap
*Last updated: August 2026*

---

## STATUS LEGEND
- ✅ Complete
- 🔄 In Progress  
- 📋 Planned
- 💡 Future Enhancement

---

## PHASE 1 — Terminal Dashboard ✅
19 tabs built and operational. Dash app launched via
pywebview on port 8050. Tabs: Portfolio, Sector/Geography,
Correlation Matrix, Market Maps, Compare Mode, Economic
Indicators (FRED), Backtesting, Alerts, Crypto, Bot Control,
Analyst Ratings, Dividend Tracker, Options Flow, Short Interest,
News. Custom CSS, dark theme, responsive layout.

---

## PHASE 2 — Schwab Integration ✅
OAuth flow, auto token refresh (30-min), portfolio sync,
order execution framework. Account: 91897389.
Files: schwab_client.py, schwab_tokens.json, schwab_status.json

---

## PHASE 3 — Signal Layer ✅
58-feature signal vector. Sources: market, momentum,
sentiment, macro. FRED API, Alpha Vantage news sentiment,
Finnhub analyst ratings. full_signal_collector.py

### Phase 3.5 — GPU Benchmark ✅
RTX 5070 12GB. PyTorch 2.11+cu128, Pyro 1.9.1, CuPy 14.1.1.
5,000 MCMC samples optimal. Full pipeline ~75 seconds.

---

## PHASE 4 — Regime Detection ✅
Stability dial (0-1). Fixed weights: vol 0.40, credit 0.30,
traj 0.15, divers 0.15. Zero fitted parameters.

### Phase 4.5 — SVI Covariance ✅
98% of NUTS posterior width in 75s vs 4:41. Certified.

---

## PHASE 5 — Portfolio Engine ✅
5-model blend: Risk Parity, Min Variance, Max Diversification,
Equal Weight, Black-Litterman. MCMC over correlations.
Transaction costs modeled (0.05% per side).

### Backtest Results (static configs, 2004-2026):
Key finding: static high-equity configs all cluster in same
band. Only equity floor and crisis response matter.

---

## PHASE 5.5 — Adaptive System 🔄

### COMPLETED:
- ✅ SH, PSQ, TBF, DBMF added to universe
- ✅ 5 scenario configs (bull_calm/bull_late/stress/crisis/recovery)
- ✅ Adaptive backtest v1 running (results tonight)
- ✅ Global monitor 24/7 built and wired to terminal
- ✅ All global markets: US/Asia/Europe/MENA/Futures
- ✅ Dividend architecture designed
- ✅ Two-reserve system designed
- ✅ Sell architecture designed

### Adaptive Backtest v2 (all improvements):
- 📋 Fractional thresholds: 0.32/0.52/0.72 (not 0.35/0.55/0.75)
- 📋 Hysteresis: fast to arm, slow to disarm
       Upgrade: immediate
       Downgrade: need -0.05 buffer + 2-3 weeks minimum
       Crisis exit: 3 weeks below threshold required
- 📋 Crisis threshold lowered to 0.72 (catches Sept 2008)
- 📋 Recovery config tightened (dial must fall >0.08 from peak,
       stay below crisis for 3 weeks)
- 📋 Proportional leverage per dial reading:
       bull_calm: 1.20 - (dial x 0.30)
       stress:    0.80 - (dial - 0.52) x 0.50
       crisis:    0.50 - (dial - 0.72) x 0.70
- 📋 Proportional short sizing per dial:
       stress SH:  (dial - 0.52) x 0.30 → 3-6%
       crisis SH:  0.06 + (dial - 0.72) x 0.18 → 6-14%
       crisis PSQ: (dial - 0.72) x 0.10 → 0-5%
- 📋 DBMF scales with stress: 5%/6%/8%/12%
- 📋 Refined blends: bull_calm momentum 50%, crisis min_var 60%
- 📋 Min trade size 1%, min 1 week holding per scenario
- 📋 Hard safety rules:
       VIX > 40 → force crisis regardless
       Dial > 0.92 → force crisis regardless

### Schwab Margin Account (MANUAL ACTION REQUIRED):
- 📋 Open margin account (1-2 days)
- 📋 Variable leverage via margin
- 📋 Margin cost modeled (~7-8% APY on borrowed)

### Dividend Architecture:
- 📋 80% dividends reinvested automatically in same ETF
- 📋 20% → Reserve A (Dividend Reserve, LOCKED)

### Reserve A — Dividend Reserve (YOUR CONTROL ONLY):
- 📋 Bot CANNOT touch this under any circumstance
- 📋 Held in SWVXX money market (~5% APY)
- 📋 Released ONLY by your Slack DIVEST command
- 📋 Weekly Slack summary with balance
- 📋 No minimum floor — accumulates indefinitely

### Reserve B — ETF Sale Reserve (BOT CONTROLLED):
- 📋 Source: rebalance trims, stop-loss sales, ejections
- 📋 NEVER from dividends — completely separate
- 📋 Bot deploys when ALL conditions met:
       1. Dial drops >0.10 from baseline
       2. Scenario is bull_calm or bull_late
       3. Balance > $500
       4. No pending Slack confirmations
       5. >7 days since last deployment
- 📋 Deploys 50% of balance (75% if dial < 0.25)
- 📋 $200 hard floor always maintained
- 📋 Slack notification AFTER deployment (not before)
- 📋 Hard barrier: bot code physically cannot access Reserve A

### Sell Architecture (5 triggers):
- 📋 Trigger 1: Weekly rebalance trim
       Only if drift > 2%, tranches if > 15% portfolio
- 📋 Trigger 2: Scenario switch de-risking
       Sell highest-momentum ETFs first, keep XLV longest
       Execute over 2-3 days
- 📋 Trigger 3: Per-ETF stop loss
       >15% drop from cost basis → Slack alert
       >25% drop → automatic sell, no authorization needed
       Exceptions: GLD, TLT (no stop loss), SH/PSQ (inverse)
- 📋 Trigger 4: Constituent deterioration (Phase 6)
- 📋 Trigger 5: Universe ejection (Phase 6)

### Sell Execution Rules:
- 📋 Never sell first 30 min of market open
- 📋 Prefer 11am-2pm ET (most liquid)
- 📋 Never sell on options expiration Friday
- 📋 Large sells (>20% portfolio) require CONFIRM
- 📋 30-second override window for stop losses
- 📋 Cost basis tracking per lot (FIFO)
- 📋 Prefer lots held >1 year (long-term capital gains)
- 📋 December tax loss harvesting
- 📋 Wash sale prevention (no rebuy within 30 days)

### Intra-Week Circuit Breakers:
- 📋 +0.15 dial move → YELLOW: prepare to de-risk
- 📋 +0.25 dial move → ORANGE: de-risk immediately
- 📋 +0.30 dial move → RED: Slack alert + emergency rebalance
- 📋 Dial > 0.85 → CRISIS: hard override

### Paper Trading Gate (ALL 4 required):
- 📋 Sharpe >= 1.1
- 📋 Max drawdown <= 30%
- 📋 Calmar >= 0.35
- 📋 Final value >= $70,000

---

## PHASE 6 — Enhanced Intelligence 📋

### Constituent Monitoring:
- 📋 Watch ALL constituents (not just top 20)
- 📋 VTI: all 11 SPDR sector ETFs as proxy (3,800 stocks)
- 📋 QQQ: all ~100 Nasdaq-100 stocks
- 📋 EEM/SCHF: country ETF proxies
- 📋 XLF/XLV: all individual stocks (~65-67 each)
- 📋 6 signals per ETF:
       1. Breadth (% stocks above 20-day MA)
       2. Dispersion (returns spreading = late cycle)
       3. Downside concentration (% stocks declining)
       4. Vol divergence (stock vols rising before ETF vol)
       5. Tail events (stock down >10% = contagion risk)
       6. Momentum divergence (ETF vs constituents)
- 📋 Event-driven: only activates on stock move >2%
- 📋 Contagion detector:
       Check sector peers + correlations + news sentiment
       Score 0 (isolated) to 1 (systemic)
       Score > 0.6 → escalate to dial
- 📋 Microadjustment (event-driven, not continuous scan):
       Stock down 5%  → ETF weight -1%
       Stock down 10% → ETF weight -3%
       Stock down 25% + high contagion → scenario switch
- 📋 TSM (Taiwan Semi) as global tech bellwether
- 📋 Weight in dial: 10%
- 📋 Build as live signal first, backtest later

### Equity Risk Premium Signal:
- 📋 Earnings yield (1/PE) vs 10yr treasury (free)
- 📋 Would have flagged 2022 overvaluation earlier
- 📋 Weight in dial: 5%

### Online Learning — Thresholds:
- 📋 Weekly performance scoring vs SPY
- 📋 Slow threshold adjustment: 0.002/week maximum
- 📋 Hard safety constraints:
       Crisis: never above 0.82, never below 0.60
       Bull-calm: never above 0.45, never below 0.20
       VIX > 40: force crisis (cannot be learned away)
       Reversion force if drift > 0.08 from baseline
- 📋 Lookback: 12 weeks, weighted toward recent
- 📋 Constituent signal → temporary -0.03 threshold boost (2wks)
- 📋 Slack notifications on ALL threshold changes
- 📋 Dashboard: current vs baseline thresholds

### Online Learning — Blend Weights:
- 📋 Monthly review of model performance
- 📋 Shift blend toward better-performing models
- 📋 Learning rate: 0.005/month
- 📋 Bounds: no model below 5% or above 60%

### Autonomous ETF Universe Selection:
- 📋 Broad scan: ~800 liquid ETFs
- 📋 Event-driven: activates on any ETF move >2%
- 📋 Composite scoring:
       Momentum (35%): 6-month return/vol
       Diversification (25%): correlation to portfolio
       Liquidity (15%): >$10M daily volume
       Regime fit (15%): fits current scenario?
       Quality (10%): expense ratio, AUM, tracking error
- 📋 Active universe: top 15-25 ETFs by score
- 📋 Updated weekly, microadjusted intra-week
- 📋 Dynamic expansion by scenario:
       bull_calm: adds SOXX, MTUM, XBI
       crisis: strips to core defensive only
- 📋 Quality filters: >$10M volume, <0.75% expense ratio,
       not duplicate, >2 years history

### Three-Bot Architecture:
- 📋 Growth bot (90% equity, momentum-heavy)
- 📋 Balanced bot (75% equity, current — already built)
- 📋 Conservative bot (45% equity, min-var)
- 📋 Meta-allocator slider 1-5 maps capital split
- 📋 All three run SVI in parallel
- 📋 News modifier per personality:
       Conservative 12%, Balanced 8%, Growth 3%
- 📋 Correlation regime detection:
       Avg correlation > 0.65 → adds 5% GLD + 5% TLT tail hedge
- 📋 Drawdown circuit breaker:
       -15% from rolling peak → pause risk trades
       Requires manual AUTHORIZE to re-risk

---

## PHASE 7 — Paper Trading 📋
- 📋 $100,000 simulated, real prices
- 📋 All three bots running simultaneously
- 📋 +5% target unlocks Phase 8
- 📋 30-day minimum paper trading period
- 📋 Slack daily P&L, weekly summary
- 📋 Constituent monitor live (observation only)
- 📋 Threshold learning live (observation only)

---

## PHASE 8 — Live Trading 📋
- 📋 Real money via Schwab
- 📋 Max 40% single ETF position
- 📋 All reserve systems active
- 📋 Constituent monitor integrated into dial (10%)
- 📋 Threshold learning applied to live thresholds
- 📋 Daily P&L to Slack, weekly summary
- 📋 Monthly strategy review
- 📋 Quarterly model retraining

---

## PHASE 9 — Full Autonomous Operation 📋
- 📋 Three-bot meta-allocator live
- 📋 Autonomous ETF universe selection active
- 📋 All online learning systems active
- 📋 Tax optimization module (FIFO, harvesting, wash sales)
- 📋 Performance attribution reporting

---

## PHASE 10 — Export Ready 📋
- 📋 FastAPI wrapper
- 📋 Multi-account support
- 📋 Risk reporting (PDF)
- 📋 Immutable audit trail
- 📋 Docker containerization
- 📋 Rate limiting + auth

---

## INFRASTRUCTURE

### Global Market Monitor ✅ (built today):
- 24/7, checks every 5 minutes
- Sessions: Futures/Asia/MENA/Europe/Americas
- ~166 instruments globally
- YELLOW/ORANGE/RED/CRISIS alerts
- 30-minute cooldown per level
- Wired into Bot tab dashboard

### Resource Targets:
GPU: 65-70% target, 80% ceiling
CPU: 50-60% target, 75% ceiling
RAM: 8-10GB target, 20GB ceiling

---

## PENDING MANUAL ACTIONS:
- 📋 Open Schwab margin account
- 📋 Confirm SWVXX as money market for reserves
- 📋 Set dividend split % (default 80/20, configurable)
- 📋 Set Reserve B threshold (default $500)

---

## CURRENT STATUS:
- Adaptive backtest v1: RUNNING (~21%, results tonight)
- Next: v2 backtest with all improvements
- Then: paper trading if gate passed

---

## ADDENDUM — Adaptive Dial System (added Aug 2026)

### Full 5-Layer Adaptive Dial Architecture:

#### Layer 1: Raw Signal Computation (fixed, never changes)
- VIX percentile, credit spread percentile, trajectory, dispersion
- Just measuring reality -- no adaptation here
- stability_index.py

#### Layer 2: Component Weights (slowly adaptive) NEW
- Current fixed weights: vol 0.40, credit 0.30, traj 0.15, divers 0.15
- Problem: credit lags in post-crisis recovery (2010 issue)
  Credit stays elevated long after VIX normalizes
  Keeps dial artificially high, bot stuck in bull_late/stress
- Solution: weights adapt based on which component
  predicted drawdowns most accurately recently
- Learning rate: 0.003/week maximum
- Bounds:
    vol:    never below 0.25, never above 0.55
    credit: never below 0.15, never above 0.45
    traj:   never below 0.05, never above 0.25
    divers: never below 0.05, never above 0.25
    sum always = 1.00
- Example adaptation:
    2010 post-crisis: credit lagging → reduce credit weight
    vol already normalized → increase vol weight
    Dial drops from 0.43 → 0.38 → triggers bull_calm earlier
    2008 crisis: credit most predictive → increase credit weight
- Slack notification on weight changes:
    "Dial weights updated:
     vol: 0.40→0.43, credit: 0.30→0.27
     Reason: credit component lagging vol by 3+ weeks"

#### Layer 3: Threshold Adjustment (slowly adaptive)
- Where are the scenario cutoffs?
- Learned from which switches added alpha vs SPY
- Learning rate: 0.002/week maximum
- Bounds:
    bull_calm: never above 0.45, never below 0.20
    crisis:    never above 0.82, never below 0.60
- Slack notifications on all threshold changes

#### Layer 4: Constituent Nudge (real-time, temporary)
- Breadth/momentum divergence adjusts effective dial ±0.05
- Resets each week at Sunday rebalance
- Fast and responsive to intra-week market internals
- Does NOT permanently change the dial

#### Layer 5: Hard Overrides (never adaptive, cannot be learned away)
- VIX > 40 → force crisis regardless
- Dial > 0.92 → force crisis regardless
- These are absolute safety rules

### Dashboard additions (to build after backtest):
- 📋 Bot tab: show all 5 dial layers live
- 📋 Current component weights (vol/credit/traj/divers)
- 📋 Baseline weights vs current weights
- 📋 Current thresholds vs baseline thresholds
- 📋 Active constituent nudge (if any)
- 📋 Which hard overrides are armed
- 📋 Weight/threshold change history chart
- 📋 "Learning mode" toggle (on/off for paper trading)

### Why this fixes the 2010 problem:
