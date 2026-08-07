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

### Inner ETF Constituent Scanning:

Pre-built CONSTITUENT_PEERS map:
  Each stock → parent ETFs + peer stocks + sector + flags

Scan triggers:
  Normal stocks:     >3% move
  Bank stocks:       >2% move (higher contagion risk)
  China tech:        >1% move (regulatory gap risk)
  TSM:               >2% move (global tech bellwether)

Inner scan cascade (max 3 calls per event):
  1. Peer scan: fetch all sector peers (1 batch call)
  2. Compute sector contagion score (0-1)
  3. If banks involved: check KRE vs XLF divergence
  4. If TSM: trigger global tech scan

Contagion scoring:
  sector_breadth × peer_magnitude × 10
  < 0.40: isolated event, minor ETF adjustment
  0.40-0.70: sector stress, reduce ETF weight
  > 0.70: high contagion, escalate to dial system
  > 0.85: systemic risk, force crisis check

Special flags:
  contagion_risk HIGH (banks):
    - Auto-check all bank peers
    - Lower trigger threshold
    - No cooldown on re-scan
    
  global_tech_bellwether (TSM):
    - Triggers global tech ETF scan
    - Affects EEM, EWT, SOXX simultaneously
    - Slack note on every significant move
    
  regulatory_risk HIGH (China tech):
    - 1% trigger threshold (gaps happen fast)
    - Check FXI, KWEB, MCHI simultaneously

API calls for inner scans:
  Normal event:  1 call (peer batch)
  Bank event:    3 calls (peers + KRE + rates)
  TSM event:     3 calls (peers + global tech + Asian ETFs)
  Worst case day (20 events): 60 calls
  
Total daily budget including inner scans: ~550 calls
Yahoo Finance limit: 2,000 calls
Comfortable headroom maintained

### ETF Due Diligence — Constituent Risk Evaluation:

Before adding ANY new ETF to active universe:
  Run full constituent risk scan
  Order all stocks by composite risk score
  Go/no-go decision based on portfolio rules

5 risk dimensions per constituent:
  1. Volatility (30-day realized vol)
  2. Momentum quality (Sharpe of 20-day returns)
  3. Fundamental health (P/E, growth, debt)
  4. Contagion risk (VIX correlation)
  5. ETF weight (concentration flag >8%)

Composite risk score: 0.0 (safest) to 1.0 (riskiest)

Go/no-go criteria (ALL required):
  Weighted avg risk < 0.65
  No single stock > 12% weight
  High-risk weight < 40% of ETF
  Fundamental health > 60% of stocks
  Momentum quality > 0.40 weighted avg
  No constituent earnings this week

Position sizing from risk analysis:
  base_size = 5%
  adjusted = base_size × (1 - weighted_risk × 0.5)
  further adjusted for concentration and risk weight
  Result: smaller positions in riskier ETFs

Ongoing monitoring after adding:
  Weekly: full constituent re-scan
  Daily: top 5 constituents quick check
  Real-time: constituent event peer scan

Slack approval flow:
  Bot presents full analysis
  Highlights safest and riskiest constituents
  Flags earnings dates for constituent stocks
  Proposes adjusted position size
  Waits for APPROVE or SKIP


---

## FULL SESSION ADDITIONS (August 5 2026)

### ADAPTIVE DIAL — Complete Architecture

6-Decimal Precision Dial:
- Replace 2-decimal with 6-decimal (0.000001 precision)
- Matches precision of market price data
- Enables truly continuous position sizing
- No more hard cliffs between scenarios
- Every 0.000001 change = proportional position adjustment

Continuous Position Sizing Formula (replaces scenario math):
  equity_pct = max(0.18, 0.90 - dial x 0.714)
  leverage   = max(0.20, 1.20 - dial x 0.986)
  dbmf_pct   = min(0.15, 0.05 + dial x 0.10)
  sh_pct     = max(0, (dial - 0.52) x 0.185)
  psq_pct    = max(0, (dial - 0.72) x 0.093)
  tbf_pct    = max(0, (dial - 0.52) x 0.092)
  defensive  = max(0.05, 1.0 - equity - dbmf - shorts)

No scenarios driving math -- bull_calm/stress/crisis become display labels only.
Smooth continuous response. Eliminates oscillation completely.

Scenario Names as Display Zones Only:
  0.000000 - 0.320000: Bull Calm
  0.320000 - 0.520000: Bull Late
  0.520000 - 0.720000: Stress
  0.720000 - 0.850000: Crisis
  0.850000 - 1.000000: Extreme Crisis

Hard Overrides (never adaptive):
  VIX > 40: force dial = max(dial, 0.90)
  Dial > 0.92: force crisis floor
  Equity never below 18%
  Leverage never above 1.25x

---

### MULTI-RESOLUTION DIAL SYSTEM

Four tiers combined into 6-decimal dial:

Tier 1: Alpaca WebSocket (0 API calls, weight 20%)
  Real-time stream, 10 key stress tickers
  SPY, QQQ, HYG, GLD, TLT, IEF, VXX, ZB=F, ES=F, BTC-USD
  Updates every 60 seconds
  Purpose: flash crashes, immediate shocks
  Cost: free (Alpaca free tier)
  No 15-minute delay

Tier 2: Yahoo 5-min batch (288 calls/day, weight 30%)
  80 tickers in ONE batch call every 5 minutes
  Derived signals, not raw prices:
    Country breadth (percent Asia/Europe ETFs falling)
    Sector rotation (defensive vs offensive leadership)
    VIX term structure (VIX vs VIX3M)
    Credit ratio (HYG/LQD spread)
    Currency stress (Yen strengthening)
  Purpose: broader market picture

Tier 3: Daily close (1 call/day, weight 30%)
  Full 58-feature signal vector at 4:05pm ET
  All FRED data, SVI covariance
  Purpose: fundamental stress assessment

Tier 4: Weekly SVI (0 extra calls, weight 20%)
  Sunday 8pm ET, uses cached data
  Purpose: strategic positioning anchor

Combined = tier1x0.20 + tier2x0.30 + tier3x0.30 + tier4x0.20
Updates every 60 seconds, 6 decimal places

---

### 5-LAYER ADAPTIVE DIAL

Layer 1: Raw Signal Computation (fixed, never changes)
  VIX percentile, credit spread, trajectory, dispersion
  Just measuring reality

Layer 2: Component Weights (slowly adaptive) -- KEY FIX FOR 2010/2012
  Problem: credit lags post-crisis, European credit contaminated US dial
  Solution: weights adapt based on predictive accuracy
  Learning rate: 0.003/week maximum
  Bounds: vol 0.25-0.55, credit 0.15-0.45, traj 0.05-0.25, divers 0.05-0.25
  Sum always = 1.00
  Slack notification on any weight change

  Regional credit additions to fix contamination:
    EUFN trend (European bank stress): 5% weight
    EM spread proxy (EEM vs SPY divergence): 5% weight
    HYG/LQD ratio (US high yield specific): 10% weight
    Reduces single BAA10Y dependency

Layer 3: Threshold Adjustment (slowly adaptive)
  Zone boundaries adjust based on alpha vs SPY
  Learning rate: 0.002/week maximum
  Crisis: never above 0.82, never below 0.60

Layer 4: Constituent Nudge (real-time, temporary)
  Breadth/momentum divergence nudges dial +/-0.05
  Resets every Sunday at rebalance
  Does NOT permanently change dial

Layer 5: Hard Overrides (never adaptive)
  VIX > 40, dial > 0.92: absolute overrides
  Cannot be learned away

---

### COMPLETE DETECTION AND SCANNING SYSTEM

API Call Budget (daily):
  Alpaca WebSocket:     0 calls  (persistent connection)
  Yahoo 1-min batch:  390 calls  (10 tickers per call)
  Yahoo 5-min batch:  288 calls  (80 tickers per call)
  Constituent scan:    48 calls  (3 ETFs per batch)
  Event scans avg:    150 calls  (3 calls max per event)
  Daily close:          1 call   (166 tickers)
  Normal day total:   877 calls  (limit: 2,000)
  Flash crash total:  937 calls  (still within limit)
  Cost: $0

Universe Scan -- Relevance Map System:
  Pre-built map: ticker -> list of related ETFs
  When anything moves >0.5%: check map, scan related only
  NOT scanning all 800 ETFs on every move
  Max 3 cascade levels, max 3 API calls per event
  Scan cooldowns: 5-min between full scans, 10-min per ticker

Key relevance chains:
  SPY moves    -> US sectors + size ETFs
  QQQ moves    -> tech sub-sectors (SOXX, SMH, IGV)
  HYG moves    -> credit ETFs + financials
  EWJ moves    -> Asian country ETFs
  GLD moves    -> commodities + safe havens
  VIX spikes   -> volatility products
  NVDA drops   -> SOXX, SMH, QQQ, XLK, VGT
  JPM drops    -> XLF, KBE, KRE, EUFN (bank contagion)
  TSM drops    -> SOXX, EWT, EEM, SCHF (global tech bellwether)

Inner ETF Constituent Scanning:
  Pre-built CONSTITUENT_PEERS map per stock:
    parent ETFs + peer stocks + sector + special flags

  Trigger thresholds:
    Normal stocks:  >3% move
    Bank stocks:    >2% move (systemic risk)
    China tech:     >1% move (regulatory gaps)
    TSM:            >2% move (global bellwether)

  5 contagion signals per constituent:
    1. Sector breadth (percent peers falling)
    2. Peer magnitude (average peer decline)
    3. ETF weight impact (stock weight x move)
    4. Fundamental divergence (vs sector health)
    5. Special flag check

  Contagion score -> action:
    < 0.40: isolated, minor ETF microadjustment
    0.40-0.70: sector stress, reduce ETF weight 15-30%
    > 0.70: high contagion, escalate to dial system
    > 0.85: systemic, force crisis dial floor

  Special constituent flags:
    contagion_risk HIGH (JPM, BAC, WFC):
      Lower trigger threshold, no scan cooldown
      Check KRE vs XLF divergence
      SOFR proxy for interbank stress

    global_tech_bellwether (TSM):
      Every >2% move triggers global scan
      Affects EEM, EWT, SOXX simultaneously
      TSM guidance = 6-12 month forward tech demand signal

    regulatory_risk HIGH (BABA, TCEHY, JD):
      1% trigger (gaps happen instantly)
      Check FXI, KWEB, MCHI simultaneously

---

### ETF DUE DILIGENCE BEFORE ADDING TO PORTFOLIO

Full constituent risk evaluation before any new ETF added:

5 risk dimensions per constituent stock:
  1. Volatility risk (30-day realized vol)
  2. Momentum quality (Sharpe of 20-day returns, smooth vs spike)
  3. Fundamental health (P/E, revenue growth, debt ratio)
  4. Contagion risk (correlation to VIX)
  5. ETF weight (concentration flag if >8%)

Output: all constituents ranked LOW to HIGH risk
Composite score: 0.0 (safest) to 1.0 (riskiest)

Go/no-go criteria (ALL required to add ETF):
  Weighted avg risk < 0.65
  No single stock > 12% weight
  High-risk stocks < 40% of ETF weight
  Fundamental health > 60% of stocks healthy
  Momentum quality > 0.40 weighted average
  No constituent earnings this week

Position sizing from risk profile:
  base_size = 5%
  adjusted = base_size x (1 - weighted_risk x 0.5)
  Further penalties for concentration and risk weight
  Result: riskier constituent profile = smaller position

Ongoing monitoring after adding:
  Weekly: full constituent re-scan at Sunday rebalance
  Daily: top 5 constituents quick check at close
  Real-time: peer scan on any constituent event

Slack approval flow:
  Bot presents full risk-ordered analysis
  Highlights 3 safest and 3 riskiest constituents
  Flags any earnings dates in next 5 days
  Proposes adjusted position size with reasoning
  Waits for APPROVE or SKIP (never auto-adds)

---

### DASHBOARD ADDITIONS (to build after backtest)

New panels in Bot tab:

6-decimal dial panel:
  Shows tier1/tier2/tier3/tier4 component readings
  Combined dial with zone label
  1-min, 1-hr, 24-hr dial history
  Trend direction and rate of change

Component weights panel (Layer 2):
  Current vol/credit/traj/divers weights
  Baseline original weights
  Drift from baseline
  Weight evolution chart

Threshold display (Layer 3):
  Current zone boundaries vs baseline
  Learning mode toggle on/off
  Last adjustment date and reason

Constituent stress panel:
  Active ETF scans in progress
  Last 5 constituent alerts
  Current sector contagion map

Reserve dashboard:
  Reserve A: balance, last addition, yield earned
  Reserve B: balance, conditions met/not met,
             days until eligible, last deployment
  Total liquid across both reserves

Detection system status:
  WebSocket: connected/disconnected/latency
  Last 1-min update: time + dial reading
  Last 5-min update: tickers scanned
  Event log: last 10 triggered events
  API calls today: used vs 2000 limit

---

### PENDING MANUAL ACTIONS (Dan):
  Open Schwab margin account (for variable leverage)
  Open Schwab SWVXX money market (Reserve A storage)
  Set dividend split percentage (default 80/20)
  Set Reserve B deployment threshold (default $500)
  Sign up Alpaca free account at alpaca.markets
    (free tier includes real-time WebSocket data)
  Confirm reserve separation approach



---

## RISK REGISTER, FAILSAFES, AND DEVELOPMENT LAYER 3

---

### IDENTIFIED RISKS AND FIXES

#### Risk 1: Dial Lag (CRITICAL)
Observed: October 2018 -- dial=0.21 while market crashed -8%
          September 2008 -- dial missed Lehman for one week
          2012 -- European credit contaminated US dial for months
Root cause: Monthly FRED data, weekly SVI, no real-time input

Failsafes:
  Hard VIX override: VIX > 25 AND rising >20% in one day
    -> force dial minimum 0.55 regardless of FRED data
    -> cannot be overridden by any other signal
  HYG hard override: HYG drops >2% in one day
    -> force dial minimum 0.60
    -> credit market is more real-time than FRED
  SPY hard override: SPY drops >3% in one day
    -> force dial minimum 0.52 (stress zone)
    -> prevents bull_calm during obvious selloffs

Fix: 4-tier dial system (Phase 6)
  Real-time Alpaca WebSocket replaces monthly FRED lag
  Estimated lag reduction: from 1-4 weeks to 3 days
  Estimated annual return improvement: +1.7% to +3.7%

#### Risk 2: Overfitting to Historical Crisis Patterns (HIGH)
Description: v2 parameters optimized for 2004-2026 data
             Future crises may have different signatures
             Crisis threshold 0.72 chosen because 0.75 missed 2008
             This is hindsight optimization

Failsafe:
  Out-of-sample validation required:
    Train: 2004-2018 (14 years)
    Validate: 2019-2026 (7 years, includes COVID + 2022)
    If validate Sharpe < train Sharpe by >0.20: reject parameters
    
  Walk-forward validation:
    Test 20 different parameter combinations
    Use only parameters that work across ALL sub-periods
    Not just the ones that look best in aggregate
    
  Parameter bounds:
    Crisis threshold: must stay 0.65-0.80 (not tuned below 0.65)
    Leverage: must stay 1.0-1.2x (not tuned above 1.2x)
    Short sizing: must stay 5-15% max (not tuned higher)

Fix: Phase 6 online learning with strict bounds
  Parameters drift slowly toward optimal
  Hard bounds prevent runaway overfitting
  Reversion force pulls back toward baseline

#### Risk 3: Execution Slippage (MEDIUM)
Description: Backtest assumes perfect execution at close price
             Live orders execute at bid-ask spread
             During crisis: spreads widen dramatically
             ETF bid-ask in normal markets: 0.01-0.05%
             ETF bid-ask in crisis: 0.10-0.50%

Failsafe:
  Limit orders only (never market orders):
    Normal rebalance: limit at mid-price
    If not filled in 30 min: move to ask (buy) or bid (sell)
    Never chase with market orders
    
  Crisis execution rules:
    During high volatility (VIX > 30):
      Reduce trade size by 50%
      Use VWAP algorithm (11am-2pm only)
      Split large orders into 3 tranches
      
  Slippage budget:
    Model 0.15% slippage per trade in backtest
    Flag if live slippage exceeds 0.25% consistently
    Reduce trade frequency if slippage too high

Fix: Smart order routing
  Check bid-ask before placing order
  Only trade when spread < 0.10%
  Queue trades for liquid hours (11am-2pm ET)

#### Risk 4: API/Data Feed Failure (MEDIUM)
Description: Alpaca WebSocket can disconnect
             Yahoo Finance rate limits or goes down
             FRED can delay publications
             System blind during outages

Failsafes:
  Alpaca WebSocket disconnect:
    Automatic reconnect within 30 seconds
    If reconnect fails: fall back to Yahoo Finance polling
    If Yahoo fails: use last known dial reading
    Slack alert: "WebSocket disconnected, using fallback"
    
  Yahoo Finance failure:
    Primary: Yahoo Finance
    Backup 1: yfinance with different endpoint
    Backup 2: Alpha Vantage (already have API key)
    Backup 3: Finnhub (already have API key)
    If all fail: freeze positions, no rebalance
    Slack alert: "All data feeds down, positions frozen"
    
  FRED failure:
    Cache last 30 days of FRED data locally
    Use cached data if live fetch fails
    Flag if cache older than 7 days
    
  Full system failure:
    Watchdog process monitors main bot
    If bot crashes: restart automatically
    If restart fails 3 times: Slack alert + freeze positions
    Emergency contact: your phone via Slack

#### Risk 5: Margin Call Risk (MEDIUM)
Description: 1.15x leverage means borrowed capital
             If portfolio drops >15% rapidly:
             Schwab can issue margin call
             Forced liquidation at worst possible time

Failsafes:
  Margin buffer monitoring:
    Check margin utilization every 5 minutes
    If utilization > 70% of limit: reduce leverage immediately
    If utilization > 85%: emergency de-lever to 1.0x
    If utilization > 95%: Slack alert + manual intervention
    
  Leverage lockout:
    Leverage above 1.0x ONLY allowed when:
      Dial < 0.30 (very calm markets)
      Portfolio drawdown < 5% from peak
      VIX < 20
    If ANY condition fails: back to 1.0x immediately
    
  Margin call prevention:
    Keep 10% cash buffer when using leverage
    Never lever beyond 1.15x (hard coded)
    Automatic de-lever if margin warning received

#### Risk 6: Single Point of Failure (MEDIUM)
Description: Everything runs on one Ubuntu machine
             Power outage, hardware failure, kernel update
             Could stop the bot at critical moment

Failsafes:
  Local redundancy:
    Watchdog process (separate Python process)
    Monitors main bot every 60 seconds
    Automatic restart on crash
    
  Cloud backup (Phase 8):
    Mirror critical components to AWS/GCP free tier
    If local machine unreachable for >15 minutes:
      Cloud instance takes over monitoring
      No trading (safety) but Slack alerts continue
      
  UPS (Uninterruptible Power Supply):
    Hardware recommendation: APC BE600M1 (~$80)
    Gives 15-30 minutes on battery
    Enough time for graceful shutdown
    
  Position snapshot:
    Save full position state every 5 minutes
    If system restarts: loads last known state
    No position confusion after restart

#### Risk 7: Model Degradation Over Time (LOW-MEDIUM)
Description: Markets change structure over time
             Correlations that worked in 2004-2026
             may not hold in 2027-2030
             2010s: low vol, QE-driven bull market
             2020s: higher vol, AI-driven, rate-sensitive
             Model trained on past may not fit future

Failsafes:
  Performance monitoring:
    Track rolling 6-month Sharpe vs baseline
    If rolling Sharpe drops below 0.70: alert
    If rolling Sharpe drops below 0.50: pause trading
    
  Quarterly retraining:
    Retrain SVI on last 3 years of data
    Update signal percentile normalization
    Compare new vs old parameters
    Only deploy if new parameters pass gate
    
  Regime change detector:
    Monitor: correlation structure changes
    Monitor: volatility regime shifts
    Monitor: factor return reversals
    If structural break detected: pause + review
    
  Human review trigger:
    Any month with return < -8%: mandatory review
    Any 3-month period with Sharpe < 0.5: review
    Any parameter drift > 15% from baseline: review

#### Risk 8: Regulatory/Tax Risk (LOW)
Description: Frequent rebalancing creates short-term gains
             Taxed at ordinary income rate (higher)
             Wash sale rules can invalidate losses
             SEC pattern day trader rules if too active

Failsafes:
  Tax optimization:
    Track all lots with purchase date
    Prefer selling lots held >365 days
    December: harvest losses before year end
    Wash sale prevention: no rebuy within 30 days
    
  Regulatory compliance:
    Weekly rebalance: far below pattern day trader threshold
    ETFs only: highly regulated, liquid instruments
    No naked shorts: only inverse ETFs (regulated products)
    
  Tax reporting:
    Export all trades to CSV monthly
    Generate Schedule D report annually
    Flag all wash sales automatically

---

### FAILSAFE HIERARCHY

When multiple failsafes conflict, priority order:
---

### DEVELOPMENT LAYER 3 (after Phase 6)

#### Layer 3A: Predictive Dial (not reactive)
Current: dial reads current stress (reactive)
Layer 3A: dial predicts stress 1-2 weeks forward

How:
  Leading indicators added to signal vector:
    Fed funds futures (market pricing future rates)
    Options skew (put/call ratio, VIX term structure)
    Credit default swap spreads (where available)
    Insider trading activity (SEC Form 4 filings)
    Earnings revision breadth (analyst upgrades/downgrades)
    
  Machine learning on top of dial:
    Input: current 58 features
    Output: predicted dial 1-week forward
    Model: LSTM (Long Short-Term Memory)
           Trained on 2004-2023 data
           Validated on 2024-2026
    
  Combined predictive dial:
    current_dial × 0.60 + predicted_dial × 0.40
    
  Benefit:
    Position for crisis BEFORE it appears in dial
    Position for recovery BEFORE dial falls
    Estimated improvement: +0.5-1.0% annual
    Estimated Sharpe boost: +0.10-0.15

#### Layer 3B: Multi-Asset Expansion
Current: ETFs only (13 instruments)
Layer 3B: expand to include:

  Futures (direct, not ETF proxies):
    ES futures: more efficient than SPY
    NQ futures: more efficient than QQQ
    GC futures: more efficient than GLD
    ZB futures: more efficient than TLT
    Lower cost, better liquidity, tax advantages
    Requires futures account (separate from equity)
    
  Options overlay (Phase 9+):
    Buy put options as tail hedge in stress config
    Sell covered calls in bull_calm (income generation)
    Cost: ~0.5% annual premium
    Benefit: asymmetric downside protection
    Estimated Sharpe boost: +0.15-0.25
    
  International bonds:
    EMB (EM bonds): diversification
    BNDX (international bonds): low correlation
    Adds genuine diversification beyond equity
    
  Real assets:
    PDBC (commodities): inflation hedge
    VNQ (REITs): real estate exposure
    WOOD (timber): uncorrelated to financial assets

#### Layer 3C: Sentiment Intelligence
Current: Alpha Vantage news sentiment (basic)
Layer 3C: advanced sentiment layer

  Social media sentiment:
    Reddit WallStreetBets (retail sentiment)
    Twitter/X financial accounts
    StockTwits momentum
    Contrarian signal: extreme retail bullishness = top
    
  Options market intelligence:
    Unusual options activity detection
    Large put buying = smart money hedging
    Dark pool activity (estimated from volume)
    
  Earnings call NLP:
    Process earnings call transcripts
    Management tone analysis
    Forward guidance sentiment
    Compare to previous quarters
    
  Patent/regulatory filings:
    SEC 8-K filings for material events
    FDA approvals/rejections for XLV holdings
    FTC antitrust filings for tech holdings
    
  Weight in dial: 8% (from current 0%)
  Estimated improvement: +0.3-0.8% annual

#### Layer 3D: Cross-Asset Regime Detection
Current: single stability dial
Layer 3D: identify which REGIME we're in

  8 identified market regimes:
    1. Goldilocks (low inflation, low rates, high growth)
    2. Reflation (rising inflation, rising growth)
    3. Stagflation (high inflation, low growth)
    4. Deflation (falling prices, falling growth)
    5. Rate crisis (rapid rate hikes, bond selloff)
    6. Credit crisis (spread blowout, liquidity freeze)
    7. Equity bubble (high valuations, low vol)
    8. Recovery (post-crisis normalization)
    
  Each regime has optimal asset allocation:
    Goldilocks: 90% equity, momentum, 1.15x leverage
    Stagflation: 30% equity, commodities, TIPS, gold
    Rate crisis: TBF heavy, short duration, no bonds
    Credit crisis: cash, GLD, SH, crisis config
    
  Regime detector:
    Neural network trained on 1970-2026 data
    Inputs: 58 current signals + dial reading
    Output: probability distribution over 8 regimes
    
  Portfolio selection:
    Blend allocations weighted by regime probabilities
    If 60% Goldilocks + 40% Rate crisis:
      Blend Goldilocks and rate crisis portfolios
      
  Benefit:
    2022 rate crisis: regime detector flags EARLY
    Shifts to TBF-heavy, short duration immediately
    Not waiting for credit spreads to widen
    Estimated improvement in 2022: +5-8%
    
  Overall estimated boost: +0.5-1.0% annual

#### Layer 3E: Portfolio Insurance Module
Current: inverse ETFs as reactive hedge
Layer 3E: proactive insurance structure

  Permanent tail hedge (0.5-1% of portfolio):
    Buy SPY put options 10% out of money
    3-month expiry, roll monthly
    Cost: ~0.5% annual premium
    Payoff: 10x+ in 2008/2020-style crashes
    
  Variance swap exposure (via DBMF):
    DBMF already provides some variance exposure
    Increase to 10% permanent allocation
    
  Correlation hedge:
    When portfolio correlation spikes (crisis):
      All positions move together = diversification fails
      Add BTAL (market neutral, anti-beta)
      BTAL goes UP when correlations spike
      Natural hedge for correlation breakdown
      
  Dynamic hedge ratio:
    Hedge size scales with dial reading
    dial < 0.35: 0.5% hedge (cheap insurance)
    dial 0.35-0.55: 1.0% hedge
    dial 0.55-0.75: 2.0% hedge
    dial > 0.75: 3.0% + inverse ETFs
    
  Estimated annual cost: 0.5-1.0%
  Estimated crisis protection value: 3-8%
  Net benefit: positive in volatile regimes

---

### COMPLETE DEVELOPMENT TIMELINE

Phase 5.5 (current):
  Adaptive backtest v1 (running now)
  Build v2 with all brain improvements
  Run v2 overnight
  
Phase 6 (after v2 passes gate):
  4-tier dial system
  Constituent monitoring
  Online learning (thresholds + weights)
  Autonomous ETF universe
  Regional credit signals
  Equity risk premium signal
  
Phase 7 (paper trading):
  30-day minimum
  All Phase 6 systems running
  Calibrate vs backtest predictions
  Validate 4-tier dial improvement
  
Phase 8 (live trading):
  Real money, Schwab margin account
  All failsafes active
  Reserve A + B live
  Full sell architecture
  
Phase 9 (Layer 3 enhancements):
  Predictive dial (LSTM)
  Multi-asset expansion (futures)
  Sentiment intelligence
  Cross-asset regime detection
  Portfolio insurance module
  
Phase 10 (export ready):
  Docker containerization
  Multi-account support
  FastAPI wrapper
  Audit trail
  
---

### PERFORMANCE TARGETS BY PHASE

Phase 5.5 v2 backtest:
  Sharpe: 1.1 - 1.2
  Max DD: -16% to -20%
  Final:  $92,000 - $108,000
  Calmar: 0.45 - 0.60

Phase 6 (live, 4-tier dial):
  Sharpe: 1.2 - 1.4
  Max DD: -14% to -18%
  Annual: 11% - 13%

Phase 7 (paper trading target):
  Sharpe: 1.2 - 1.5
  +5% in 30 days to unlock Phase 8

Phase 8 (live trading):
  Sharpe: 1.3 - 1.5
  Max DD: -12% to -16%
  Annual: 12% - 14%

Phase 9 (full system):
  Sharpe: 1.4 - 1.7
  Max DD: -10% to -14%
  Annual: 13% - 16%
  $10,000 → $140,000-$185,000 over 21 years

### v3 Candidate: Magnitude-Scaled Hysteresis

Problem: fixed 2-3 week exit delay treats a 0.05 whipsaw and a
0.45 regime collapse identically. Costs re-risking speed at
V-shaped bottoms (March 2009 scenario).

Fix: scale the required wait by how far the dial fell from peak.

    drop = peak_dial - current_dial
    weeks_needed = max(1, round(base_weeks - drop / 0.12))

Validated behavior:
  From peak 0.90 (crisis unwind):
    drop 0.05 -> 3 weeks   (noise, hold)
    drop 0.15 -> 2 weeks
    drop 0.25 -> 1 week    (real move, act)
    drop 0.45 -> 1 week
  From peak 0.54 (2004 whipsaw):
    drop 0.04 -> 3 weeks   (protection intact)
    drop 0.11 -> 3 weeks
    drop 0.16 -> 2 weeks

Status: designed and behavior-tested, NOT applied to v2.
Apply only if v2 log shows slow recovery off the 2009 bottom
(check ~21% mark vs v1 trough of $11,325 in Feb 2009).

Alternative considered: price confirmation (SPY +12% off 60-day
low bypasses hysteresis). Independent signal, but adds a
dependency and may fire on bear market rallies. Lower priority.

---

## V3 PLAN (after v2 results)

### 1. Magnitude-Scaled Hysteresis

Problem: fixed 2-3 week exit delay treats a 0.05 whipsaw and a
0.45 regime collapse identically. Costs re-risking speed at
V-shaped bottoms (March 2009 scenario).

Fix: scale required wait by how far the dial fell from peak.

    drop = peak_dial - current_dial
    weeks_needed = max(1, round(base_weeks - drop / 0.12))

Validated behavior:
  From peak 0.90 (crisis unwind):
    drop 0.05 -> 3 weeks   (noise, hold position)
    drop 0.15 -> 2 weeks
    drop 0.25 -> 1 week    (real move, act fast)
    drop 0.45 -> 1 week
  From peak 0.54 (2004 whipsaw):
    drop 0.04 -> 3 weeks   (protection intact)
    drop 0.11 -> 3 weeks
    drop 0.16 -> 2 weeks

Use round() not int() to avoid a cliff at drop=0.25 where
2009-style moves land.

Trigger condition: apply if v2 log shows slow recovery off the
2009 bottom. Compare ~21% mark against v1 trough of $11,325
(Feb 2009) and v1 recovery to $13,927 by Aug 2009.

### 2. Price Confirmation Override (lower priority)

If SPY is up >12% off its 60-day low, bypass hysteresis entirely
and allow immediate downgrade. Independent signal from the dial,
so it catches recoveries the dial is slow to register.

Risk: may fire on bear market rallies (Nov 2008 had a +19% bounce
mid-crisis). Would need a second condition -- perhaps requiring
the dial to also be falling -- before this is safe.

### 3. Stress Exit Timing Review

v2 exits stress after 2 weeks (stress_exit_weeks=2). Whether this
is right is untested. Check the 2011 US downgrade and 2015-2016
China selloff sections of the v2 log for evidence of exiting too
early (portfolio drops right after downgrade) or too late
(sitting defensive through a recovery).

### 4. Open Questions for v3

- Does bootstrap dial (300 samples) meaningfully smooth threshold
  crossings vs point estimate? Compare scenario switch counts
  between v1 and v2 logs.
- Is DBMF 8% minimum the right floor? Test 6% and 10% variants.
- Should GLD minimum scale with dial rather than fixed 4%?
- Market dial weights (credit 0.35 / vol 0.30 / rate 0.18 /
  intl 0.10 / gold 0.07) were set by hand. Worth a sensitivity
  sweep once v2 baseline exists.

### v3 Evidence: Hysteresis Overcorrection Confirmed

Observed in v2 run, May-June 2005 (GM/Ford credit event):
  Apr 15  dial=0.50  stress   (correct entry)
  May 20  dial=0.32  stress   (dial collapsed, still held)
  May 27  dial=0.27  stress   (bull_calm territory, still held)
  Jun 03  dial=0.23  stress   (deeply calm, still stuck)

Dial fell 0.27 in three weeks -- clearly a regime change, not
noise -- but fixed hysteresis held stress config (~55% equity)
when ~74% was appropriate.

Magnitude-scaled formula would have released on May 20:
  drop = 0.50 - 0.32 = 0.18
  weeks = max(1, round(3 - 0.18/0.12)) = max(1, round(1.5)) = 2
  ...and fully by May 27 (drop 0.23 -> 1 week).

Also investigate: bot appears to hold longer than
stress_exit_weeks+1 = 3 weeks implies. Check whether weeks_in
counter resets on same-level updates, or whether the bull_late
downgrade branch has an unintended extra condition.

Cost in this instance was small (portfolio still rose on bond
and gold strength). Would be larger off a sharp equity bottom.

### v3 Sequencing Decision

Do magnitude-scaled hysteresis ALONE in v3. Reasons:
  - Deterministic, verifiable against known failure cases
  - Single change means clean attribution of any improvement
  - May be sufficient on its own -- it adapts to drop size,
    which is the actual signal distinguishing noise from regime
    change

Defer self-correcting/learned hysteresis to Layer 3. Failure
mode: hysteresis protects against rare events, so evaluating it
during calm stretches (2013-2019) makes every hold look like a
mistake. Bot relaxes the parameter, then 2020 arrives with the
protection optimized away.

If learned version is built later, required guardrails:
  Learn only from episodes where dial exceeded 0.60
  Max 0.1 weeks adjustment per episode
  Hard bounds: 1 to 4 weeks
  Reversion toward 2.5 weeks when idle
  Minimum 10 episodes before any adjustment
  (~3-4 qualifying episodes per decade, so decades to move
  meaningfully -- which is appropriate)

### BUG TO INVESTIGATE (before v3)

May-June 2005: entered stress Apr 15, still in stress Jun 03.
That is 7 weeks, but stress_exit_weeks + 1 = 3 should allow exit
once dial < 0.44. Dial was 0.32 by May 20 and 0.23 by Jun 03.

Check:
  - Does weeks_in reset on same-level updates?
  - Does the bull_late downgrade branch have an unintended
    extra condition?
  - Is the recovery branch intercepting before bull_late is
    reachable?

Find this before adding magnitude-scaling on top.

### v3 Candidate: Piecewise Continuous Allocation

Problem: current continuous_allocation uses one straight line
(slope -0.714) across the entire dial range 0-1. This means the
calm zone (dial 0.0-0.35, most of 2004-08, 2013-19, 2023-26) gets
the same sensitivity as the crisis transition zone, capping
equity around 83-90% even at the calmest readings -- a candidate
explanation for underperforming SPY's 100% exposure.

Fix: piecewise curve, three segments, each with its own slope,
continuous at every junction (no cliffs), still a pure function
of dial with NO memory of prior state.

    dial < 0.35:  equity = 0.90 - d * 0.20   (gentle, protect bull runs)
    0.35-0.68:    equity = 0.83 - (d-0.35) * 1.161   (steep, real transitions)
    dial >= 0.68: equity = 0.447 - (d-0.68) * 0.616  (gentler taper, near floor)

Rate limiter (15% down / 6% up per week) sits on top unchanged.
Only the target-generating function changes.

Guardrail: must stay stateless. If any version of this needs to
remember which segment it was in last week to decide behavior,
that reintroduces the state-machine trap risk from tonight's
three bugs. Verify with a pure function test:
f(dial) always returns the same output regardless of call history.

Test protocol before any real backtest:
  1. Swap continuous_allocation -> continuous_allocation_v3
     in dryrun_v2.py only
  2. Run dryrun_v2.py (~20s), check:
     - latch check still <= 2 weeks (confirms still stateless-safe)
     - equity/dial correlation still < -0.5
     - NEW: compare mean equity during dial<0.20 weeks against
       v2's current curve -- should be meaningfully higher
  3. Only then apply to the real adaptive_backtest_v2.py

Do not implement until current full run (started 2004-06-30)
completes and its calm-period vs SPY comparison is read first.
This is a response to a hypothesis, not yet a confirmed leak.

---

## LIVE OBSERVATIONS FROM v2 RUN (2008 SECTION)

Watched in real time as the backtest progressed through 2008-2009.
Two distinct failure modes identified, different from the earlier
state-machine bugs -- these are dial/response-curve issues, not
bugs, and both need real evidence before fixing.

### Failure Mode A: Lehman-week lag (Sept-Oct 2008)
Dial climbed 0.52 -> 0.58 -> 0.64 through Sept 12-26 but didn't
cross into crisis (0.69) until Oct 3 -- portfolio dropped $12,209
-> $10,578 (-13.4%) in that single week before crisis config
engaged. This is a weekly-rebalance / weekly-dial-check structural
limit, not a bug -- confirming a regime change takes several
readings, and Lehman was violent enough to do most of its damage
before confirmation completed.

Candidate fix: daily dial computation (compute_market_implied_dial
already supports any date) while keeping weekly trading. Cheap to
test -- same historical data, no live feed needed, isolates
whether check-frequency alone would have caught this earlier.

### Failure Mode B: flat dial during grinding decline (Dec 2008 - Feb 2009)
Dial sat 0.61-0.67 for ~8 weeks while market kept making new lows.
Portfolio drifted $11,529 -> $10,111 (-12.3%) with equity held
roughly constant the whole time, because dial genuinely wasn't
moving, not because of any lag or bug. Different problem: the dial
measures "how bad does this feel right now," not "is this still
getting worse even slowly."

Three candidate fixes discussed, NOT yet chosen between:

  1. Trend/momentum term: add rolling drawdown-from-recent-high
     into the dial computation directly, so sustained slow declines
     register even when nothing single-day is scary.

  2. Steeper response curve in the 0.55-0.70 band specifically:
     same dial readings, but continuous_allocation moves equity
     more per unit of dial in that zone (extension of the
     piecewise-curve idea already logged above).

  3. Duration/persistence signal: if dial stays above ~0.55 for
     N+ consecutive weeks without breaking back below ~0.40, treat
     sustained stress as its own escalating signal, independent of
     any single reading's magnitude. Currently nothing in the
     system distinguishes "one bad week" from "eight mediocre weeks
     in a row" -- they can produce the same dial reading.

Decision on which of these three (if any) to build: DEFERRED until
full run completes. Required before choosing: pull every stretch
in the completed backtest where dial sat flat for 6+ weeks and
check what price action was doing underneath each one. If
consistently "flat dial + still declining," points at #3
(duration). If mixed results (sometimes flat-and-fine), points at
needing a genuinely separate signal (#1, trend) rather than
amplifying the existing one.

### Sequencing
Do not build any of these mid-run. After full run completes:
  1. Read final results and OOS split first
  2. Pull the flat-dial-stretch evidence described above
  3. Choose ONE candidate fix per failure mode based on that
     evidence, not on tonight's guesses
  4. Test via dryrun_v2.py before any real backtest commitment

---

## STANDING INSTRUCTION FOR WHEN v2 FULL RUN COMPLETES

When the current overnight run (started 2004-06-30, tracked in
adaptive_backtest_v2_log.txt) finishes and produces the full
results block (final value, Sharpe, OOS split, scenario
breakdown, drawdown), synthesize ALL of the following into ONE
recommended path forward -- not a list of options, an actual
recommendation for each open question, using the full 22-year
evidence rather than the single 2008 instance each was spotted in.

### Open questions to resolve with full evidence:

1. Lehman-week lag (weekly dial check too slow for violent
   single-week shocks). Check whether the same lag pattern
   appears at other fast shocks -- 2018 Feb Volmageddon, 2020
   COVID March, 2015 Aug China deval. The 2010 Flash Crash was
   NOT a good test of this (it reversed same day, weekly rebalance
   never saw it).

2. Flat-dial grinding decline (Dec 2008-Feb 2009, dial stuck
   0.61-0.67 while market kept falling). Check whether this
   recurs in 2011 European debt crisis, 2015-16 China slowdown,
   2022 rate-driven grind. Build the duration/persistence signal
   ONLY if it repeats. If 2008-specific, don't build it.

3. Rate-limiter recovery drag (flat 6%/week re-risk cap, ~19
   months to reclaim 2008 peak -- though that beat SPY's own ~5
   year recovery on calendar time). Check 2011, 2020 (COVID
   snap-back, best stress test -- even faster than 2009), 2022
   recoveries. Recommend magnitude/duration-scaled re-risk rate
   ONLY if cost shows up repeatedly, not just in 2009.

4. 2010-style dial chop / component disagreement (May-Aug 2010,
   dial oscillating 0.20-0.53, no clear trend). Four fixes were
   proposed with zero evidence: collapse to single number,
   reweight components, add new components (news sentiment),
   require persistence/consensus. REQUIRED FIRST: pull individual
   component scores (credit/vol/rate/intl/gold separately, not
   blended dial) for that period plus any other chop periods
   found in the full run (check 2015-16, 2018 Q4). Determine:
   noisy signal (fix it) vs accurate reflection of genuinely mixed
   conditions (leave it alone). Recommend ONE approach only if
   diagnostic shows a real recurring defect.

5. Piecewise continuous allocation curve (steeper/gentler slopes
   by dial zone). Test via dryrun_v2.py: does raising the
   calm-zone equity ceiling close any real gap vs SPY, based on
   full-run calm-period returns vs actual SPY returns over the
   same calendar windows.

6. Overall verdict vs SPY and vs the stated gates. Full final
   value, Sharpe (weekly and corrected daily), Calmar, max
   drawdown, OOS Sharpe (train 2004-2018 vs validate 2019-2026).
   State plainly whether it beat SPY on both return AND Sharpe --
   the standard set as the actual goal -- not just whether it
   cleared the original four-gate checklist (separately
   acknowledged as somewhat arbitrary).

### Required output format:

For items 1-5: state what the full-run evidence actually shows
(repeated pattern vs one-off single instance), then give ONE
clear recommendation -- build it, don't build it, or build a
specific named alternative -- reasoned from evidence across
multiple periods in the completed run, not the single instance
each was originally spotted in during tonight's live commentary.

Then ONE overall recommended next step, not a menu. Decision, not
another list of tradeoffs.

Do not recommend building anything based on single-instance
evidence from tonight alone -- cross-check against the full run
first.

---

## ARCHITECTURAL DIRECTION: HIERARCHICAL "SPLIT MIND" DESIGN

Distinct from the reactive patch list above. This is a structural
direction for the whole project, not a fix for a specific bug
observed tonight. Proposed during live discussion while watching
the Taper Tantrum section (2013) expose that international/EM
stress gets blended into the single main dial rather than being
seen and reacted to on its own terms.

### The core idea

Right now: ONE dial, ONE decision. All signals (credit, vol, rate,
intl, gold) blend into a single number that drives the single
biggest lever (overall equity vs defensive split). This is
deliberately simple -- validated hard tonight, stateless, provably
non-latching via the rate limiter. That simplicity is why it was
debuggable at all after three earlier state-machine failures.

Proposed next layer: multiple SMALL, NARROW-SCOPE watchers, each
fully aware of its own domain, each empowered to act ONLY within
its own slice -- feeding up to, but not overriding, the main
decision-making dial.

    Layer 1 (exists, validated tonight):
      Main dial -> overall equity vs defensive split
      US-centric signals, deliberately filters foreign noise
      (this is WHY the 2012 European-contamination problem
      was fixed -- do not lose this property)

    Layer 2 (proposed, not yet built):
      Narrow watchers, each with full visibility into their
      own domain, each acting ONLY on their own allocation
      slice, never touching the main equity/defensive split:
        - EM/international watcher -> adjusts EEM/SCHF weight
          within the equity sleeve only
        - Sector watchers (eventually) -> adjust XLF/XLV weight
          within the equity sleeve only
      Full visibility, CONTAINED reaction. A regional or sector
      problem should size its own position down, not force the
      whole portfolio defensive.

    Layer 3 (already logged earlier, further out, live-only):
      Individual stock/constituent-level awareness inside ETFs,
      event-driven, cannot be backtested historically, requires
      live data feeds.

### Why this over "add more inputs to the one dial"

Most of tonight's brainstorming (reweighting, adding signals,
persistence requirements) was about improving ONE dial's
accuracy. This is different: it's about NOT forcing every kind of
stress through one blunt global lever in the first place. A
contained regional problem should get a contained regional
response. Blending it into the main number either drowns it out
(current state -- Taper Tantrum only nudged the dial 0.27->0.56
despite EEM itself dropping ~15%) or, if overweighted, risks
recreating the exact 2012 contamination problem this whole
redesign was built to fix.

### Why this matters more for live trading than backtesting

In a backtest, a blunt whole-portfolio overreaction to a contained
problem just shows up as a worse number at the end. Live, with
real capital, an unnecessary whole-portfolio de-risk over a
contained regional issue has a real cost (transaction costs,
lost upside) that compounds every time it happens. Getting
proportional response right before live capital is involved is
worth doing properly.

### Guardrails for whenever this is built (learned hard tonight)

- Each new watcher must be STATELESS or use the same
  rate-limiter pattern already validated (no discrete
  states/labels with hysteresis -- that pattern failed three
  times tonight before being replaced).
- Each watcher must be independently testable via a dryrun-style
  script BEFORE integration, same as continuous_allocation was
  validated in isolation before the full backtest ran.
- Layer 2 watchers must be provably unable to override Layer 1's
  main equity/defensive decision -- only adjust weights WITHIN
  the equity sleeve. This containment is the entire point; if a
  regional watcher can force the whole portfolio defensive, it
  has recreated the single-dial problem with extra steps.

### Status

Architectural direction only. NOT scheduled for this backtest
cycle. Build only after:
  1. Full v2 run completes and single-dial baseline is understood
  2. Post-run review confirms international/regional blindness is
     a real, recurring, costly gap (not just the one Taper
     Tantrum instance) -- same evidence-first bar as every other
     item on this list
  3. Layer 1 is fully stable and well-understood on its own

### Family rule (added after discussion)

Every Layer 2+ watcher, no matter how narrow or small its scope
feels, must pass the SAME three validation steps used on the main
dial tonight before integration -- no exceptions for watchers that
seem low-stakes because they only touch one small slice:

  1. Isolated pure-function test: feed it a long synthetic
     sequence, confirm it converges to target, confirm nothing
     repeats/latches for more than ~2-3 consecutive periods
     (same latch check used in dryrun_v2.py tonight)
  2. Real historical date sanity check: run it against several
     known real events in its domain, confirm output direction
     and magnitude make sense (same method as the 10-date market
     dial validation)
  3. Full dry-run pass (no SVI, cheap, ~20s) before any real
     backtest commitment

A watcher that seems small is EASIER to miss a latch bug in, not
safer -- it only affects one slice, so nobody notices as fast as
they'd notice the main dial breaking. Smallness is not a reason
to skip validation; if anything it's a reason to be more careful,
since bugs there are quieter.

---

## RESERVE SYSTEM REDESIGN (replaces dividend-based version)

Original design (earlier in this file, "Reserve A/Reserve B"
section) is superseded by this. Reasoning: a reserve funded from
20% of dividends is sized to an unrelated income stream, not to
actual portfolio risk. A $200k portfolio in low-yield growth ETFs
could generate a trickle of dividends while carrying far more
risk than that trickle is sized to cover. Fix: size the reserve
to portfolio value directly, and fund it through the mechanism
that already exists rather than inventing a new one.

### New design

  - Dividends: 100% reinvested automatically. No more 80/20 split.
  - Safety reserve target: a fixed percentage of current total
    portfolio value (number TBD -- 10-15% is the working range,
    not yet fixed).
  - Funding mechanism: redirected from Reserve B's existing
    inflows (cash generated by ordinary rebalance-driven sales --
    already a normal, expected side effect of the bot doing its
    regular job). NOT a new scheduled sale, NOT dividend-sourced.
  - Rule: on any rebalance-driven sale that generates cash, the
    first portion (up to whatever keeps the safety reserve at
    target) is redirected to the safety reserve. Only the excess
    above that continues to Reserve B's normal deployment logic
    (buying back in during calm-post-stress conditions, as already
    designed).
  - Bot has full control of pulling FROM the safety reserve when
    conditions warrant (unlike the original Reserve A, which was
    locked to the user only). This is a deliberate change --
    since the reserve is now sized to actual portfolio risk and
    funded mechanically rather than manually, it's safe to let the
    bot redeploy it under the same rules Reserve B already uses.

### Why this over alternatives considered

  - Rejected: scheduled quarterly trim regardless of market
    conditions. Risk: could force a sale into weakness if the
    trim date lands during a crash.
  - Rejected: fully manual (user pulls dividends into a side
    account by hand). Re-adds a manual step the mechanical
    version avoids.
  - Chosen: redirect from Reserve B inflows. No forced sale that
    wouldn't otherwise happen -- just changes where already-moving
    cash goes. Stays fully mechanical.

### Open items before building

  - Exact target percentage of portfolio value (10%? 15%? not
    yet decided).
  - What happens during a long calm bull run with few/no
    rebalance-driven sales -- reserve could stay under target for
    an extended period since nothing is generating inflow to
    redirect. Needs a fallback (possibly a small scheduled top-up,
    ONLY as backstop if under target for 6+ months, not as the
    primary mechanism).
  - Confirm this doesn't reintroduce a hidden third lever
    competing with the dial's equity/defensive split -- the
    safety reserve is explicitly OUTSIDE that split, a separate
    pool, not a third state to reconcile with the other two.

Status: designed, not built. Depends on the same evidence-first
gate as everything else -- confirm via post-run review whether
the calm-zone equity ceiling should actually be raised (this
reserve redesign is part of the justification for doing so), then
build both together rather than in isolation.

---

## DE-ESCALATION TIMING: STOPGAP FIX + WHY SPLIT-MIND SUPERSEDES IT

### Evidence (two confirmed instances, different years, different causes)

1. Dec 2008-Feb 2009: dial sat 0.61-0.67 (flat, not de-escalating
   fast enough) while market kept making new lows. Severe cost
   (~-12% over 8 weeks).

2. Nov 23-30, 2018: dial hit crisis (0.70), then dropped to
   bull_late (0.48) just ONE WEEK later -- de-escalated too fast.
   Market made a new low the following week (Dec 7), proving the
   de-escalation premature. Milder cost, but same mechanism: the
   decision to step back down from defense is being made too
   easily, on too little confirmation, relative to how hard the
   decision to step INTO defense is required to be.

Two instances, one on each side of "how fast should de-escalation
happen" -- together they show the actual problem isn't sensitivity
in general, it's a specific asymmetry: entering defense works
well (confirmed clean across 2011, 2014, Volmageddon, this same
Q4 2018 section's initial escalation), exiting defense is too
easy relative to entering it.

### Stopgap fix (buildable now, testable via dryrun_v2.py)

Require sustained improvement, scaled to how severe the peak was,
before the rate limiter is allowed to start re-risking at all --
not a fixed wait for every case, proportional to peak severity:

    peak >= 0.70 (crisis):   require 2-3 consecutive weeks of
                              improvement before re-risking starts
    peak 0.50-0.68 (stress): require 1-2 consecutive weeks
    peak 0.35-0.50 (mild):   require ~1 week

Implementation must stay stateless in the same sense as the rate
limiter -- a simple consecutive-weeks-improving counter that
resets the instant the dial ticks back up, not a discrete state
with its own hysteresis rules (the exact pattern that caused three
separate latch bugs earlier tonight). This is a counter gating
WHEN the existing rate limiter is allowed to act, not a new
state machine.

Validate against: Nov 2018 (should have prevented the premature
Nov 30 step-down), AND the 2011 debt ceiling / 2014 ruble
recoveries specifically (confirm the delay doesn't cost meaningful
ground in cases where danger genuinely passed fast -- both of
those resolved within 1-2 weeks in the real data, so a
1-2-week-for-moderate-stress rule should mostly not have
penalized them).

### Why split-mind architecture (logged earlier) is the better
### long-term answer, and this is explicitly a STOPGAP

The stopgap only asks "has the ONE blended number held steady/
improved for N weeks." That can't distinguish a genuine, broad
improvement (credit, vol, and rate all easing together) from a
narrow, temporary one (one noisy component swinging back down
while others stay elevated, blend just follows the swing). A
split-mind system could require genuine AGREEMENT across
independent watchers before de-escalating -- a fundamentally
stronger and harder-to-fake confirmation than one number sitting
still, which is a real limitation of the stopgap, not a small
detail.

Sequencing: build and test the stopgap now, since it's small,
fast, and directly evidenced. Do NOT treat it as the permanent
answer -- it is explicitly superseded by the split-mind
architecture once that gets built. When split-mind work begins,
the stopgap's confirmation-by-consecutive-weeks logic should be
replaced by confirmation-by-cross-watcher-agreement, not kept
alongside it.

## ETF Scorer/Tiering/Sizing -- Stability Gap Found

Built and validated tonight: score_etf(), select_universe() with
percentile+absolute-floor tiering, size_positions(). All three
checked against 2012/2017/2022 and behave sensibly and honestly
in each regime, including the 2022 concentration edge case.

REAL PROBLEM FOUND: size_positions() has no week-to-week memory --
recomputed fresh every time from that week's scores alone. Tested
across 8 consecutive weekly dates in a CALM stretch (May-June 2012)
and got single-ticker weight swings up to 17.3% even when nothing
dramatic was happening in the market. 2022 volatile stretch showed
swings up to 32.9%, some coinciding with full ticker entry/exit.

This is the same structural gap the rate limiter solved for the
equity/defensive split -- ETF-level sizing needs equivalent
smoothing before it's trustworthy in a real backtest or live
system. Root cause: tier boundary crossings (Tier 2 -> Tier 1 or
vice versa) can flip a ticker's weight multiplier in one step with
no gradual transition.

NEXT STEP (not built yet): apply a rate limiter to individual ETF
weights, same principle as the equity rate limiter -- cap max
weekly change per ticker. Needs to stay stateless-pattern-safe
(pure function bounded by previous week's actual weights, not an
accumulating internal state).

Test in isolation (cheap, no SVI) before ever wiring into a real
backtest -- same discipline used for everything else tonight.
