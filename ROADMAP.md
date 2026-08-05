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

