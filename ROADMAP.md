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

## ETF Weight Smoothing -- Flat Cap Rejected, Needs Redesign

### What was built and why it's wrong

size_positions_smoothed() applied a flat 5%-per-week cap on how
fast any ticker's weight could move toward its target, borrowing
the equity/defensive rate limiter's pattern directly. This was a
mistake -- applied by analogy without checking whether the
justification actually transfers.

The equity rate limiter's asymmetry (fast de-risk, slow re-risk)
is justified by a real safety argument: protect against a false
"all clear" being premature. ETF selection has no equivalent
argument -- it's "which acceptable option deserves more weight,"
not "is danger really over." A flat cap on ETF weight changes has
no such justification and imposes real cost: going from 0% to a
60% target takes 12 weeks at 5%/week, a full quarter of being
meaningfully underexposed to what the scorer has already
correctly identified as the best available opportunity.

### The worse, compounding failure mode (identified before building)

If the market shifts again before a slow-moving position finishes
catching up to its original target (very plausible within a
12-week catch-up window), the bot re-targets from wherever it
currently sits and starts crawling toward the NEW target instead.
If this repeats, the bot can spend extended periods perpetually
partway through a transition, never actually arriving anywhere --
a different and arguably worse form of instability than the
original noise problem, and one that would NOT show up in a short
8-week test window (need 12+ weeks of history to even see a
single full catch-up cycle, let alone a repeated-retarget loop).

This was caught through reasoning before building and testing it
against real data -- worth confirming with an actual longer-window
test (12-16+ consecutive weeks, watching for retargeting-before-
arrival) once a new design exists, rather than trusting the
correctness of the reasoning alone.

### Direction for the redesign (not yet built)

Distinguish NOISE from SIGNAL rather than applying a uniform speed
limit to all changes:
  - Small week-to-week score changes (plausibly noise): smooth/damp
  - Large, genuine score changes (real regime shift): allow fast,
    close to immediate movement toward the new target

Additionally, even for smoothed/noise-case movements, cap how far
BEHIND target the position is allowed to drift before being forced
to catch up faster -- closer to the magnitude-scaled hysteresis
idea logged earlier for the main dial, applied here instead. A
flat percentage-per-week cap with no such catch-up-forcing
mechanism is what allows the compounding-lag/retargeting-loop
failure mode described above.

### Status
Rejected: flat 5%/week cap (implemented, tested, found to have a
real theoretical flaw before deeper testing revealed it in
practice -- caught through the user's own reasoning about market
dynamics, not through the 8-week test which was too short to show
it directly).

Not yet built: noise-vs-signal distinction + magnitude-aware
catch-up mechanism. Design fresh next session, do not extend
tonight's flat-cap code further.

Everything else built tonight remains valid and tested:
score_etf(), select_universe() with percentile+absolute-floor
tiering, size_positions() (the unsmoothed version) -- all
confirmed sensible across 2012/2017/2022. Only the week-to-week
smoothing layer needs rework.

## NEXT SESSION PLAN: ETF Universe Expansion

Built and validated tonight: score_etf(), select_universe() with
percentile+absolute-floor tiering, size_positions(), and
size_positions_smoothed() with proportional (EWMA) smoothing --
all tested against 2012/2017/2022 real data, including a caught
and corrected design mistake (flat weekly cap rejected in favor
of proportional smoothing after identifying a compounding-lag
failure mode before it caused damage).

This all currently operates on CANDIDATE_UNIVERSE, a fixed
hand-picked list of 14 tickers. That is NOT the broad-universe
system discussed earlier ("scan ~800 liquid ETFs") -- it's
mechanically ready, but still working on a small fixed list, just
like the original 13-ticker universe it's meant to eventually
replace.

Agreed order for next session:

1. BROADEN THE UNIVERSE SOURCE
   Where does a genuinely large candidate list (hundreds of
   tickers) actually come from? Needs a real data source, not a
   hand-typed list. Practical constraints to solve: avoiding
   re-downloading/re-scoring hundreds of tickers fresh every
   single week when most won't have changed meaningfully --
   caching strategy needed.

2. REAL LIQUIDITY / ELIGIBILITY FILTER
   Current liquidity score in score_etf() is a placeholder using
   history length as a stand-in, not real volume data -- adequate
   for 14 already-liquid, hand-picked ETFs, NOT adequate for a
   broad screen where some candidates could be genuinely illiquid.
   Needs real volume-based filtering before scoring even runs.

3. HANDLE UNIVERSE MEMBERSHIP CHANGES, NOT JUST WEIGHT CHANGES
   Everything built tonight assumes the candidate list itself is
   fixed and only weights shift within it. A real system needs to
   handle: a ticker becoming newly eligible (no prior weight to
   smooth from -- already partially handled), AND a ticker leaving
   eligibility entirely (delisted, become illiquid, no longer
   relevant) -- a different kind of event than a weight adjustment,
   not yet designed.

4. WIRE INTO A CHEAP DRY-RUN TEST BEFORE ANY REAL BACKTEST
   Same discipline used successfully tonight (dryrun_v2.py) --
   test the full scoring/tiering/sizing/universe pipeline cheaply
   before ever connecting it to adaptive_backtest_v3.py or
   committing to a multi-hour run. Find out if ETF selection
   genuinely adds value on top of the existing dial-driven
   equity/defensive split, or interacts with it unexpectedly,
   BEFORE spending real compute time on it.

Start fresh next session with item 1. Everything from tonight
(scorer/tiering/sizing/smoothing) is solid and tested -- this is
additive work on top of it, not a rebuild.

## Defensive Sector Rotation -- Tested Against 5 Real Crises

### The idea
Instead of reducing total equity exposure during stress (current
system's approach), stay near 100% equity but rotate composition
toward historically defensive sectors (XLV healthcare, XLP
staples) rather than growth (QQQ, SOXX). Would preserve full
market participation during calm periods (closing the SPY gap)
while still offering some crash protection through lower-beta
holdings.

### Real test: peak-to-trough drawdown, single-holding, across
### 5 distinct crisis types (perfect-timing ceiling, not a
### realistic backtest -- see limitations below)
### Findings
- XLP (staples) consistently the best rotation target, beating
  XLV in 4 of 5 crises tested.
- XLP beats or ties bonds (TLT) specifically when bonds themselves
  get hurt -- 2022's rate crisis is the clear example (TLT -39.1%,
  worse than XLP's -16.3%). This matters: our current system's
  defensive sleeve leans on bonds, which is NOT safe in every
  crisis type.
- Rotation alone is roughly comparable to our actual system in
  2008 (tie) and 2022 (system slightly better).
- Rotation alone is CLEARLY worse than our actual system in 2020 --
  the fastest crash in the dataset. Staples still fell 24.5% vs
  our system's ~17.8%, because a fast enough crash drags down all
  equities together regardless of sector defensiveness. This is
  exactly where active de-risking + shorts earn their keep, and
  where staying at 100% equity (however composed) cannot help.

### Honest conclusion
Rotation is a real, legitimate technique -- not a weaker version
of doing nothing, genuinely competitive with the current system
in slower-moving crises. But it does not consistently beat what
exists now, and clearly underperforms in fast/violent crash types.
Strongest likely use: as an ADDITIONAL input layered onto the
current system's equity sleeve during stress (e.g. the min-var
blend already tilts toward defensive names -- could be made more
deliberate/aggressive about it), NOT a wholesale replacement for
dial-driven exposure reduction + shorts.

### Limitations of this test (important)
- Single-holding peak-to-trough with perfect timing, not a
  realistic backtest. Real rotation logic has lag, same as the
  dial does -- actual results would be worse than this ceiling.
- Only checked XLV/XLP as rotation targets. Other defensive
  sectors (XLU utilities, low-vol factor ETFs) not yet tested.
- 5 crises is a reasonable sample but not exhaustive -- worth
  testing against 2015-16 China slowdown and any other distinct
  crisis character if this gets built further.

### Status
Real, tested idea. Not yet built into anything. Worth considering
as a refinement to the existing equity-sleeve blend logic (min-var
weighting during stress) rather than a standalone system, once
the ETF universe expansion work is further along.

## Dynamic Universe Test -- Early Real Signal (July-Aug 2006 crisis)

Running adaptive_backtest_v3_dynuniverse.py (dial+ceiling+dynamic
universe combined vs v2 baseline, NOT isolated -- v3 alone never
finished last night so v2 is the only clean baseline available).

Consistent lead over v2 across ~30 real checked dates spanning
calm periods and stress. Most notable: during a genuine crisis
reading (dial=0.75, July 14 2006), the gap widened sharply to
$718-1,082, far larger than the $200-600 typical of calm-period
checks. Since total equity/defensive split is IDENTICAL between
the two systems during a crisis (same dial, same rate limiter),
this gap can only be coming from WHICH equities are held during
the pullback -- direct evidence the dynamic universe is adding
real value specifically during stress, not just calm periods.
Gap narrowed back to $270-399 as conditions calmed, consistent
with composition mattering less once equity exposure normalizes.

Still early (11% through). Two real tests remain before drawing
a conclusion: 2008's genuine severe crisis (does this hold up
under real pressure, or was 2006 too mild a test), and the long
calm stretches 2013-2019 / 2023-2026 (where last night's
ceiling-only test lost its early momentum once checked deeper).

IMPORTANT CAVEAT: this run cannot cleanly separate "ceiling
change" from "dynamic universe" since v3-alone was never
completed as a clean baseline. If this run's full result looks
good, a follow-up isolating JUST the dynamic universe against
the ORIGINAL v2 formula (no ceiling change) would be needed to
know how much of any improvement is attributable to universe
selection specifically vs the ceiling change riding along with it.

## SESSION SUMMARY -- Where Things Actually Stand

### Confirmed solid, trust this:
- Market-implied dial: validated on 10 real historical dates,
  correctly separates real crises from noise (2012 EU contagion
  correctly stayed calm, 2018 blind spot fixed)
- Rate limiter: replaced the 3x-latching state machine, confirmed
  stateless and non-latching across 2008/2011/2018/2020/2022
- ETF scorer/tiering/sizing/smoothing mechanism: built and tested
  correctly at the mechanism level (dry run, 1153 weeks, all
  checks pass)

### Tested and inconclusive/negative -- do not build further on
### these without new evidence:
- Equity ceiling raise (0.90->1.00 base): mixed across 4 real
  historical windows in v3, no consistent improvement over v2
- Dynamic ETF universe for equity selection: initial dramatic
  result was a BUG (bonds/TLT leaking into equity sleeve,
  double-counting the defensive sleeve's job). Once genuinely
  fixed (bonds excluded from CANDIDATE_UNIVERSE), a real short-
  window test (2007-2013, corrected for a separate phantom-row
  bug) showed -36.6% max drawdown, WORSE than the established
  ~-25% to -33% baseline. This is a real, sobering result, not
  explained away -- the honest equity-only selection may simply
  be less protective during 2008 than the accidental bond-heavy
  version was.

### New tools built this session, ready for future use:
- backtest_windows.py: short (~2hr) curated test windows
  (2007-2013 crisis+recovery, 2019-2023 COVID+2022) instead of
  full 22yr (~7hr) runs, for fast iteration before committing to
  a long run
- Fixed a real bug in this new tool: the last-week fallback
  (`next_d = ... else px.index[-1]`) reached all the way to
  TODAY's live price data on bounded windows, producing a
  phantom final record that corrupted every summary stat.
  Fixed: falls back to repeating the last real date instead.
  Full 22yr runs (v1/v2) were NEVER affected by this -- their
  natural end date was already close to px.index[-1].

### Conclusion reached this session:
Two consecutive nights of incremental changes to the SAME core
architecture (dial-driven equity/defensive split + various equity
sleeve refinements) have not produced a clean, consistent
improvement. Neither the ceiling change nor the dynamic universe
(once correctly fixed) closed the gap to SPY or improved crisis
protection. This is real evidence that the next useful change is
likely STRUCTURAL -- a genuine redesign of how the dial governs
the portfolio -- rather than another incremental parameter or
sub-system tweak on top of the existing architecture.

### Next session: structural dial redesign
User has indicated wanting to discuss structural changes to the
dial itself, plus "a few changes to our system" -- not yet
specified. Start fresh next session with this full context loaded
rather than re-deriving it. Do NOT default back to tuning
parameters on the existing architecture without first having the
structural conversation.

## NEXT SESSION: MULTI-DIAL ARCHITECTURE (real redesign, not a tweak)

### The core problem, stated precisely
The current system compresses all market information into ONE
number (the dial), then makes ONE decision (equity vs defensive
split) based on it. This means genuinely different situations
that happen to produce the same dial reading get treated
identically -- a regional currency shock (e.g. China deval) and
a systemic credit freeze (e.g. Lehman) could both read as 0.65,
but they warrant completely different responses. By the time you
see the blended number, the information about WHICH kind of
stress is happening has already been destroyed.

This is not a new observation -- the "split mind" idea was
discussed and agreed on as the right direction weeks before this
session, then never built. Two full nights were then spent tuning
PARAMETERS inside the single-dial architecture instead (ceiling
formula, equity sleeve selection) -- neither produced a clean win.
That's real evidence the single-dial container itself, not its
parameters, is the actual bottleneck.

### The proposed structure
Multiple independent, narrow dials, each watching one domain:

  CREDIT dial: HYG/LQD, US-specific credit stress
  VOLATILITY dial: VIX direct, market-wide fear
  CURRENCY/EM dial: EEM vs SCHF divergence, dollar strength --
    catches regional/EM-specific shocks (China deval, EM crisis)
    without triggering a systemic-level response
  RATE dial: yield curve, TLT/SHY -- catches slow rate-driven
    grinds (2022-style) which are structurally different in
    character from sudden credit freezes (2008-style)

Each dial computed independently, same market-implied approach
already validated for the current single dial (10-date real
history check before trusting any new one).

### The key architectural change: response depends on COMBINATION,
### not just magnitude
Currently: one number -> one response curve.
Proposed: which dial(s) are elevated determines the SHAPE of the
response, not just its size.
  - Currency/EM dial alone elevated, others calm: small, targeted
    reduction in EM-specific exposure. NOT a broad equity pullback.
  - Credit + volatility + rate all elevated together: correctly
    read as closer to systemic, broad pullback + shorts, similar
    to current crisis behavior.
  - This is what "cannot tell a China deval from Lehman" actually
    means fixed -- the RESPONSE becomes different because the
    SIGNATURE across dials is different, even at similar overall
    severity.

### Why this is a real architecture change, not a tweak
This is not "add a signal to the blend" (already tried, e.g. the
5-signal blend inside the current single dial). It's restructuring
HOW the decision gets made -- from one number driving one curve,
to multiple numbers driving a combination-aware response. Real,
substantial design work. Do not rush this at the end of a long
session -- start fresh.

### Required discipline carrying forward from this session's
### hard-won lessons (do not repeat these mistakes):
1. Each new dial must be validated against 10+ real historical
   dates BEFORE trusting it, same as the original market-implied
   dial was.
2. Any position-sizing/response logic must be pure-function/
   stateless, same rate-limiter pattern already proven -- no new
   state machines, no repeat of the 3x-latching saga.
3. Test cheaply first (dry run, no SVI) before ANY multi-hour
   backtest commitment.
4. When a result looks dramatically good, check ACTUAL HOLDINGS
   directly before trusting the aggregate number -- this is
   exactly what caught the TLT bug, and should be step one, not
   a last resort after hours of runtime.
5. Use backtest_windows.py (short 2007-2013 / 2019-2023 windows)
   for iteration. Only run the full 22-year backtest once a short
   window already looks correct.
6. Watch for the specific failure mode already caught once this
   session: a bounded-window backtest run must be checked for
   phantom end-of-range artifacts (confirmed bug, now fixed, but
   worth remembering the failure signature: an impossible final
   jump in the reported final value).

### Open sub-questions to resolve when actually designing this
(not yet decided):
- Exactly how many dials, and which specific domains -- 4
  proposed above (credit/vol/currency-EM/rate) is a starting
  point, not final.
- How does "combination" translate into actual position sizing --
  needs a real, specific formula, not just the qualitative
  description above.
- Does each dial get its own equity-sleeve-style sub-selection
  (e.g. does the currency/EM dial specifically control EEM/SCHF
  weight, separate from the credit dial controlling something
  else), or do all dials feed into ONE combined equity/defensive
  decision with the combination logic only affecting how much/
  how fast, not which specific assets?
- Should this replace the current single dial entirely, or run
  alongside it during a transition/comparison period the way the
  dynamic universe ran alongside v2 tonight?

## MULTI-DIAL ARCHITECTURE -- FINALIZED DESIGN (v2 of the plan)

Supersedes the "combination-aware single decision" version logged
earlier this session. That version still funneled everything to
one final number -- user correctly pushed back that the system
should make MULTIPLE simultaneous moves, not just one, as long as
those moves can't collide.

### The core design principle
Multiple dials, each with its OWN exclusive, non-overlapping
lever. No two dials can ever touch the same resource. This is not
a coordination rule to remember and enforce -- it's a hard
structural boundary, the same way TLT's bug (two systems reaching
for the same asset) becomes IMPOSSIBLE by construction rather than
prevented by convention.

### The four dials and their exclusive levers

CREDIT dial (HYG/LQD, US-specific)
  Owns: overall equity vs defensive split
  This is the current system's dial, doing its current job,
  unchanged in what it controls.

VOLATILITY dial (VIX direct)
  Owns: rate-limiter SPEED -- how fast the credit dial's target
  gets approached, not WHAT is held. High vol = move faster
  toward whatever the credit dial has already decided. Does not
  touch composition or sizing directly, only tempo.

CURRENCY/EM dial (EEM vs SCHF divergence, dollar strength)
  Owns: EEM/SCHF weight specifically, as its own slice within
  whatever total equity allocation the credit dial has set. A
  China-deval-style shock trims this slice alone -- the credit
  dial's overall equity percentage doesn't need to move at all.

RATE dial (yield curve, TLT/SHY)
  Owns: TBF/duration hedge exposure -- its own small, dedicated
  sleeve, separate from both the main equity sleeve and the EM
  slice. This is what should have specifically caught 2022 (a
  rate-driven grind where bonds themselves got hurt) without
  needing the credit dial to also react.

### Why this resolves both original concerns
1. Genuinely simultaneous, independent decisions -- not one
   blended number. A currency shock produces real, specific
   action (EM slice trimmed) without touching the broader equity/
   defensive split at all.
2. Cannot recreate the TLT bug. There is no asset or decision any
   two dials could both claim, because each lever is exclusively
   owned. Not prevented by a rule -- prevented by there being no
   shared resource to fight over in the first place.

### Still open, needs real design work before building:
- Exact formula for how the volatility dial's "speed" modifier
  interacts with the existing rate limiter (multiply the existing
  step size? A separate multiplier bounded to some range?)
- Exact sizing for the EM slice and the rate/duration sleeve --
  how large is each allowed to get relative to the whole
  portfolio, and does either have its own ceiling/floor
- Whether the EM slice and rate sleeve are carved OUT of the
  credit dial's equity allocation (reducing what's left for
  everything else) or ADDED on top as their own separate buckets
  -- this affects total portfolio composition math and needs to
  be decided precisely, not implicitly

### Build order (once above is resolved)
1. Validate each new dial's raw signal against 10+ real historical
   dates BEFORE any of them touch portfolio logic (same discipline
   as the original market-implied dial)
2. Build each lever's formula in isolation, test standalone
   (same pattern as continuous_allocation() being testable alone)
3. Combine only after each piece is independently verified
4. Dry-run test (no SVI) across the full 1153-week history,
   checking specifically: do the four levers ever produce
   contradictory or nonsensical combined output, same latch/
   sanity checks used for every prior dry run this session
5. Short-window backtest (backtest_windows.py) before any full
   22-year run

## Currency/EM Dial -- Debugging Session, Real Progress, Fix Pending

Built dial_currency_em.py as the template for the multi-dial
architecture. Genuine progress and real bugs found and fixed:

1. Detection layer validated properly via validate_signal_separation()
   -- real stressed-vs-calm comparison (not single-event eyeballing,
   which gave a false "GOOD" verdict initially). Real result:
   stressed mean 0.904, calm mean 0.531, only 4.9% overlap. Signal
   IS legitimate, contrary to an earlier mistaken conclusion this
   session that it was "just noisy."

2. First action-layer bug found and fixed: relative z-score vs
   trailing 26-week mean failed to trigger AT ALL during real 2013
   Taper Tantrum, because the trailing baseline became contaminated
   by the crisis's own leading edge. Fixed with an absolute bar
   (0.905) instead, derived from the real stressed-period median.

3. Second bug found (root cause took 3 debugging attempts and 2
   wrong diagnoses to isolate -- worth remembering the process,
   not just the fix): using the STRESSED-period median (0.905) as
   the bar means roughly half of genuine crisis weeks read BELOW
   it by definition, causing real, legitimate stress periods to
   trigger false releases. Real percentile check against calm-only
   history: 90th percentile of calm readings = 0.857. This is a
   better, calm-anchored bar -- clearly above normal variation,
   with real headroom below typical crisis readings (0.85-0.99),
   not sitting exactly on the boundary the stressed-median bar did.

4. THIRD bug diagnosed but fix NOT YET APPLIED: strict consecutive-
   week counting (3 in a row unusual to engage, 3 in a row normal
   to release) is too brittle -- a single legitimate noisy dip
   during ongoing real stress (confirmed present in actual April-
   May 2013 data) resets the counter and can cause premature
   release even mid-crisis. Proposed fix (designed, not yet
   correctly applied to the file due to a failed text-match edit):
   replace strict consecutive counting with a TRAILING WINDOW
   FRACTION -- e.g. engage if >=75% of the last 4 weeks are
   unusual, release only if <=25% of the last 4 weeks are unusual.
   Tolerant of normal single-week noise in either direction without
   losing the persistence requirement entirely.

### Also worth remembering: the debugging process itself
This session's dial-building went through THREE consecutive wrong
diagnoses before finding the real bug each time (relative-z-score
contamination theory -- correct; "signal is noisy" theory -- WRONG,
fixed by proper stressed-vs-calm validation; consecutive_normal
locals() bug -- correct but not the full picture; finally the real
bar-placement + persistence-brittleness issues). This is normal
and expected for genuinely new signal engineering, but it's worth
noting HOW LONG it took (many iterations) as a planning input for
building the remaining three dials -- budget real time for this
per dial, don't expect it to go faster just because the pattern is
now established.

### Status: NOT ready to replicate to other 3 dials yet
Fix the trailing-window persistence logic properly first (edit
failed to apply this session -- verify actual file state before
continuing, do not assume prior edits landed). Then re-validate
against full-year 2013 AND check it doesn't introduce new false
releases/engagements elsewhere (e.g. run against a genuinely calm
year like 2005 or 2017 to confirm it stays silent). Only once this
ONE dial is fully correct should the same template get replicated
to volatility, rate, and (already-existing, needs no rebuild)
credit dials.

## Rate Dial -- Real Progress, Not Yet Finished

Built dial_rate.py following the proven currency/EM/volatility
template. Detection layer validates well (separation +0.599,
0.6% overlap -- comparable to the other two dials).

Action layer found a genuine, distinct false-fire pattern,
different in character from currency/EM's blind spot:
- Original: 13/52 false fires in 2017, caused by TLT genuinely
  RISING (real bond rally) being misread as "stress" by the
  ratio-based percentile, since unusual-in-either-direction was
  being treated as stress-in-one-direction.
- First fix (absolute decline check, same pattern as currency/EM):
  reduced to 7/52. Remaining fires traced to a genuinely CHOPPY,
  non-trending period (TLT bounced 91.92->91.15->93.46->89.98->
  91.05 in early 2017) where a simple "below 63 days ago" check
  flips unpredictably depending on which two points in the chop
  get compared.
- Second fix (require >1% meaningful decline, not just any
  negative sign): reduced to 4/52 false fires, BUT also reduced
  real 2022 crisis detection from 37/43 to 34/43 weeks -- a real
  cost, not free. This is the same sensitivity/specificity
  tradeoff discussed conceptually all session, now directly
  measured rather than theoretical.

### Honest assessment
Three consecutive threshold/confirmation tightening passes are
showing diminishing returns -- each buys some false-fire reduction
at a real, measurable cost to genuine detection. This suggests
TLT/SHY is a genuinely noisier signal in its normal state than
either currency/EM or volatility, and further threshold tweaking
on the SAME mechanism is unlikely to solve it cleanly.

### Next steps to actually try (not yet attempted):
- Longer/smoother lookback window for the underlying ratio itself
  (not just the decline-confirmation check) -- may reduce
  noise at the source rather than filtering after the fact
- Consider whether TLT/SHY is even the right pair -- maybe the
  actual yield curve (e.g. 10yr-2yr spread, if that data is
  available) would be a cleaner, more direct signal than a bond
  ETF price ratio
- Do NOT keep tightening the same absolute-decline threshold
  further -- diminishing returns already demonstrated

### Status of all three dials attempted this session:
- CURRENCY/EM: complete, validated, committed (0 false fires in
  2017 after fix, correct 2013 Taper Tantrum detection preserved)
- VOLATILITY: complete, validated, committed (0 false fires in
  2017 with NO additional fix needed, correct Volmageddon
  detection)
- RATE: real progress, not finished. Detection layer solid,
  action layer needs a different approach than threshold-tightening,
  not more of the same fix. Pick up fresh next session.
- Fourth dial (credit) already exists as the original main dial,
  no rebuild needed.

## ALTERNATIVE ARCHITECTURE IDEA: Graduated Static Bot Blending

Discussed as a genuinely different structural approach from the
multi-dial continuous-formula system built this session. Not yet
built, worth comparing against the multi-dial approach once both
have real results.

### The idea
Instead of one continuously-adjusting portfolio driven by a
formula (current approach), maintain several complete, pre-built,
individually-validated static portfolios (like the original
Balanced/Growth/etc. configs from early this session) representing
distinct market regimes. The dial's job becomes selecting which
whole static portfolio to gradually blend toward, rather than
tweaking individual formula parameters.

Extension discussed: don't just have 4 distinct bots (Calm/
Bull-late/Stress/Crisis) with linear math interpolating between
them -- build genuine INTERMEDIATE static bots too (e.g. "Mild
Caution" between Calm and Stress, "Serious Concern" between Stress
and Crisis), each independently tested and validated the same way
the four original ones were. This means blending only ever happens
between two known-good, individually-checked waypoints, rather
than trusting a formula to produce sensible behavior at every
possible point on a continuous line -- most of which was never
directly tested.

### Why this might help with sudden regime changes specifically
A pre-built static bot doesn't need real-time computation --
it's already fully formed. When the dial detects a shift, the
system can start blending toward an already-validated target
immediately, rather than computing a brand-new allocation from
scratch right when speed and reliability matter most (directly
relevant to the Lehman-week lag and the volatility dial's
persistence-delay tradeoff, both found this session).

### Honest limitation, discussed directly
The actual TRANSITION speed between static bots still needs the
same careful, gradual handling as everything built this session
(rate limiter, persistence checks) -- this idea does not
automatically solve the speed/lag problem by itself. The real
benefit is CONSISTENCY of the target being blended toward (a
known, pre-tested portfolio) rather than raw speed of the
transition itself.

### Comparison to build, once both approaches have real results
- Multi-dial continuous system (this session's main work): smooth
  formula-driven adjustment, each dial owns an exclusive lever,
  validated dial-by-dial
- Graduated static bot blending (this idea): discrete, validated
  waypoints with blending only between adjacent known-good states

Not mutually exclusive -- could potentially combine (e.g. static
bots as the credit dial's targets, with the volatility/currency-EM
levers still operating independently on top). Worth exploring
which produces more reliable, more explainable behavior during
real historical regime transitions once there's actual backtest
data from the multi-dial system to compare against.

### Status: idea only, not built, no code written

## Multi-Dial Backtest Integration -- Real Bug Found, Fix Incomplete

Wired volatility and currency/EM dials into adaptive_backtest_v3.py
as real, exclusive levers (volatility -> rate limiter speed,
currency/EM -> EEM slice weight). Confirmed working correctly in
calm/mild-stress periods (small, consistent positive gaps vs v3
baseline throughout early-mid 2007 and around Bear Stearns).

REAL BUG FOUND at the actual Lehman crash (Oct 2008): multi-dial
version was $1,250-1,282 BEHIND baseline at the worst point
(Oct 3 2008), both BEFORE and AFTER a fix attempt.

First diagnosis (volatility speed multiplier applying to BOTH
de-risk and re-risk directions, causing premature re-risking
during brief mid-crisis vol dips): real bug, genuinely fixed
(multiplier now only applies to de-risking). BUT did not resolve
the Oct 3 gap -- $1,282 after the fix, essentially unchanged from
$1,250 before it. This diagnosis was WRONG, or at best incomplete
-- the volatility fix was a real, worthwhile fix on its own merits,
but it is not the (or not the only) cause of this specific gap.

### Status: NOT YET DIAGNOSED CORRECTLY
Do not assume the volatility fix solved anything until re-verified.
Real next step: isolate which lever (volatility speed OR currency/
EM EEM trim) actually causes the Oct 3 2008 gap by disabling one
at a time and rerunning just that single date/narrow window --
targeted diagnostic, not another guess. Given two consecutive wrong
diagnoses of the same gap this session (same failure pattern as
the earlier currency/EM action-layer debugging), don't guess a
third time -- isolate mechanically before proposing another fix.

## ETF Universe Expansion via Schwab API -- Real, Major Progress

Found and used a genuine, high-value data source: Schwab's own
Instruments API (already authenticated via existing schwab_client.py
connection) supports description-regex search. Built
search_instruments_by_description() in schwab_client.py.

Real pipeline built and validated:
  1. Search Schwab for "ETF" in description -> 23,490 raw results
  2. Filter to asset_type == 'ETF' exactly -> 5,473
  3. Filter symbol format (no $ prefix, no dots, reasonable
     length) -> 5,471
  4. Filter out leveraged/inverse/exotic products by description
     keyword -> 4,494 "appropriate" candidates
  5. For each candidate: download real price/volume history,
     require 2+ years of history AND real dollar volume >= $1M/day
     (same _compute_liquidity threshold already used elsewhere)

Real, measured yield rate: consistently 27-45% survive the full
liquidity/history filter, most batches landing 33-37%. This rate
held stable and consistent across 30 real batches (4,500
candidates), not just the first one -- genuinely trustworthy.

CONFIRMED: computational cost of scoring is NOT a real constraint.
91 tickers scored in the same ~0.25s as 45 tickers -- fixed
overhead dominates, per-ticker cost is ~2.8ms. No reason to cap
the universe size for performance reasons; the real constraint is
candidate quality/discovery, not scoring speed.

Built build_full_universe.py -- checkpointed, safely re-runnable,
picks up exactly where it left off (progress saved to
histdata/universe_build_progress.json).

### Progress as of stopping tonight
2,250 of 4,494 total appropriate candidates processed.
783 validated survivors found (real, liquid, appropriate ETFs).
Original target was 250-300 -- already exceeded by 2.6x.
Revised target based on measured yield rate: ~1,500 total
survivors achievable from the full candidate pool.

STOPPED due to yfinance rate limiting (YFRateLimitError hit on
the last batch) -- correct call to stop rather than push through,
given tonight's repeated lesson about not trusting data gathered
while hitting rate limits or other silent-failure conditions.

### Next session: two real, separate threads to pick up
1. Continue build_full_universe.py -- 2,244 candidates remain,
   script will resume automatically from saved progress. Space out
   batches to avoid the rate limit this time.
2. Properly diagnose the Oct 2008 multi-dial gap via isolation
   (disable currency/EM lever only, rerun; disable volatility lever
   only, rerun; compare each against the full combined version) --
   do NOT guess at a third fix without this real, targeted
   diagnostic step first.

## Data Source Split: yfinance vs Schwab (clarified)

Important distinction surfaced discussing rate limits: these two
sources serve genuinely different purposes, not redundant with
each other.

BACKTESTING/RESEARCH (yfinance): needs deep history (20+ years)
across hundreds of tickers to validate strategies against real
past regimes (2008, 2013, 2018, 2022, etc.) -- exactly what every
dial and the ETF scorer needed tonight. Free/unofficial, real rate
limits, acceptable for this use case since it's not live-money-
critical, but should be used respectfully (space out large batch
downloads, as learned tonight).

LIVE TRADING (should be Schwab, once built): does NOT need deep
history -- only needs the trailing lookback windows the live
system actually uses (63-day returns, 252-day percentile ranks,
etc. -- at most ~1-2 years back from "now"). Schwab's own API
(already authenticated, already integrated via schwab_client.py)
can very plausibly supply this directly, meaning the LIVE system
likely does not need yfinance at all once built -- removing a real
fragility point (free, unofficial, rate-limited source) from the
part of the system that will actually have real money on the line.

NOT YET BUILT: the live-data-fetching path through Schwab
specifically for the rolling lookback windows dials/scorer need.
Currently everything (including what would be live logic) is
written assuming a yfinance-sourced parquet cache. This is real,
separate work for whenever live-trading integration begins --
worth remembering this split so live-path development doesn't
accidentally inherit yfinance as a live dependency by default.

## DECIDED: Next Major Architecture Direction -- Regime-as-Distinct-Bot

Synthesis of two ideas discussed separately tonight (graduated
static bot blending + the near-100%-exposure "option 1" from the
honest-gap discussion), now combined into one real direction.

### The core shift
Current architecture: ONE continuous formula, same underlying
logic/caution baked in across the whole dial range, just scaled by
a number. This is confirmed, by real evidence, to produce a
structural drag during calm years large enough that crash
protection cannot close the resulting gap (measured: ~2x final
gap vs SPY, too wide for any plausible future crash to erase).

New direction: each regime (Calm / Mild Caution / Stress / Crisis)
becomes its OWN distinct, separately-built trading style, not a
scaled version of one shared formula.
  - CALM regime: genuinely aggressive, built to capture close to
    full market participation, none of the reflexive caution the
    current single formula always carries. This is the direct fix
    for the actual confirmed problem (calm-year drag).
  - CRISIS regime: stays exactly as protective as current design,
    untouched, separately validated -- the part that already works.
  - Mid-tier regimes (Mild Caution, Stress): genuinely intermediate
    styles, not linear interpolation between the two extremes.
  - Dial's job changes from "adjust one formula's output" to
    "decide which distinct regime/bot is currently active" +
    smooth transition between them (reusing the proportional
    smoothing logic already built and validated this session).

### Why this is a real structural change, not another tuning pass
Confirmed via real, careful testing across two sessions that
tuning parameters WITHIN the existing single-formula architecture
(equity ceiling, ETF selection, multi-dial levers) has not closed
the gap. This is not guesswork -- it's the honest conclusion from
real evidence. A structurally different approach is warranted.

### Required discipline (same as everything validated this session)
- Each regime-bot must be independently validated against real
  historical dates before trusting it, same as every dial was
- Transitions between regime-bots must use the same
  stateless/proportional-smoothing pattern already proven --
  no new state machines
- Test each regime-bot's behavior via backtest_windows.py (short,
  cheap) before any full 22-year commitment
- Specifically verify: does an aggressive Calm regime, even with
  Crisis regime unchanged, produce a WORSE overall crash outcome
  than today's system, because more of the timeline is spent in
  the aggressive style before a crisis is confirmed? This is the
  real, honest risk of this direction and must be measured, not
  assumed away.

### Status
Decided direction for next major session. NOT yet designed in
detail (exact regime boundaries, how many regimes, exact
transition logic) or built. Sequencing: finish current universe
build + Lehman-gap diagnosis first, then start this fresh.

## Lehman-Gap Diagnostic -- Tangled, Needs Clean Restart

Attempted to isolate which lever (volatility speed multiplier or
currency/EM EEM trim) causes the ~$1,250-1,282 Oct 3 2008 gap
between the multi-dial system and v3 baseline, using
DISABLE_VOL_LEVER/DISABLE_EM_LEVER environment variable toggles
added to adaptive_backtest_v3.py.

Verified the toggle LOGIC itself is correct in isolation (simple
standalone Python test confirmed: flag unset -> speed_mult=1.5,
flag set -> speed_mult=1.0, exactly as intended).

BUT: two full backtest runs (EM-disabled, then vol-disabled) that
should have shown different October 3 values instead showed
IDENTICAL results ($7,603 both times). Given the isolated logic
test proves the toggle mechanism itself works correctly, the
actual bug must be somewhere in how the environment variable
reaches the real backtest run -- NOT diagnosed before stopping.
Possible causes not yet checked: output/command mix-up during a
confusing session (one command's output may have gotten
conflated with another's -- a full RESULTS block appeared instead
of expected live progress mid-diagnostic, suggesting real
confusion in what was actually run when), a caching issue with
how compute_action_signal or the dial modules get imported across
separate subprocess invocations, or something else entirely.

### Status: genuinely unresolved, do not trust either test result
Both "Test 1" ($7,603, EM disabled) and "Test 2" ($7,603, vol
disabled) should be treated as UNVERIFIED and likely invalid given
the confirmed logic-vs-behavior mismatch. Do not conclude which
lever causes the gap from this session's numbers.

### Recommended clean restart for next session
Rather than continuing to debug env-var-based toggles (proven
correct in isolation but not reproducing correctly in the real
run), consider a cleaner isolation method:
  - Two SEPARATE, permanent script copies (like
    adaptive_backtest_v3_dynuniverse.py was built as its own file
    earlier) -- one with only the vol lever code path, one with
    only the EM lever code path -- rather than runtime toggles
    that depend on environment variable propagation working
    correctly across process boundaries
  - OR: add explicit print/log statements INSIDE the actual lever
    application code showing vol_speed_mult's real value each
    week, so the live output itself proves whether the toggle
    took effect, rather than inferring it from the final portfolio
    value alone
  - Verify carefully which terminal output corresponds to which
    command before drawing any conclusion -- this session's
    confusion (a results block appearing where live progress was
    expected) suggests output tracking itself became unreliable
    partway through, likely from running multiple things close
    together without clearly separating them

### Real, solid work this session (unaffected by the above):
ETF universe build fully complete and validated -- 1,368 real
equity ETFs, full history cached, computational cost confirmed
trivial, real bugs found and fixed (word-boundary keyword
matching). This work is solid and does not need to be revisited.

## Lehman-Gap Diagnostic -- RESOLVED CLEANLY (corrected finding)

Previous session's env-var-toggle diagnostic was tangled and
untrustworthy (documented above). Redone cleanly this session
using separate, permanent script copies instead of runtime
toggles -- adaptive_backtest_v3_vol_only.py (EM lever permanently
removed from code) and adaptive_backtest_v3_em_only.py (vol lever
permanently removed from code). Each run fully separately, full
live output tracked start to finish, no ambiguity about which
output belongs to which test.

### Real, verified results at Oct 3 2008 (the worst point of the
### crisis, where the original gap was found):

    v3 baseline (no dials at all):       $9,131
    Vol-only (EM lever removed):         $7,612
    EM-only (vol lever removed):         $7,570
    Full multi-dial (both active):       $7,849

### CORRECTED CONCLUSION
The original hypothesis (one of the two new dial levers is causing
the gap) is WRONG. Removing either lever individually makes the
result at this date slightly WORSE, not better -- and having BOTH
levers active together produces the best of the three dial-
affected results. This means:
  1. Neither the volatility lever nor the currency/EM lever is
     the cause of the v3-baseline-vs-multi-dial gap -- both were
     wrongly suspected.
  2. The real gap is between v3 baseline ($9,131) and EVERY
     dial-affected version (~$7,570-7,849) -- present regardless
     of which combination of the two new levers is active.
  3. Therefore the actual cause must be in something SHARED across
     all three dial-affected versions -- most likely the underlying
     credit dial's own behavior/computation during this specific
     week, not either of the two new levers built this session.

### Real next step (not yet done)
Investigate the credit dial's own behavior at this date -- compare
its raw dial reading and resulting equity_target between the v3
baseline run and the multi-dial runs. Since the credit dial is
supposed to be identical and untouched by the new levers (per the
exclusive-lever design), if its behavior actually differs between
runs, that would be a genuine, different bug in either the
baseline or the multi-dial setup -- possibly in how the two files
were originally forked from each other, or a real subtle
difference in data/state between the runs. If the credit dial's
raw output is confirmed IDENTICAL across all versions, the cause
is likely somewhere in the shared portfolio construction/SVI
optimization step instead. This is a real, well-scoped next
diagnostic, genuinely different from (and more promising than)
the lever-isolation work just completed.

### Status: two dial levers CLEARED of blame, real cause still open
Both dial_currency_em.py and dial_volatility.py remain trusted,
validated pieces of work from earlier sessions -- this diagnostic
confirms they are not the source of the Lehman-week discrepancy.
The actual cause is elsewhere and not yet found.

## Lehman-Gap Diagnostic -- Deeper Investigation, Real Progress, Cause Narrowed

Continued investigating why v3 baseline, vol-only, and em-only
produce genuinely different equity_target values at 2008-10-03
despite all sharing "identical" credit-dial logic.

### Ruled out with real, direct evidence:
1. Raw market-implied dial computation (compute_market_implied_dial):
   confirmed fully deterministic, identical value (0.691630) across
   3 repeated calls with same inputs.
2. Dial history feeding the bootstrap step (dial_hist, sourced from
   the static stability.parquet file): confirmed deterministic,
   stable values, correct length (52), file is static and unchanged
   across all test runs this session.
3. Bootstrap randomness in bootstrap_dial_allocation (np.random.choice
   + np.random.normal, NO seed set -- confirmed real, unseeded
   randomness exists here): measured directly across 10 repeated
   calls with identical input, equity_target varied only 0.4920 to
   0.5011 (~0.9 percentage points). Real, but too small to explain
   the actual gaps measured (which involve equity_target differing
   by 3-4+ percentage points between script versions, e.g. baseline
   0.6299 vs em-only 0.6611 at the same date).

### Real, unresolved lead (not yet checked)
SVI covariance fitting (fit_svi, called separately from the dial's
own bootstrap step) ALSO involves sampling/randomness
(n_steps/n_draws parameters seen earlier this session) and has NOT
been checked for a random seed or for how much variance it
introduces on its own. This is the next concrete thing to test --
same methodology as the dial bootstrap check just completed: call
fit_svi directly, multiple times, with identical inputs, measure
the real spread in output, compare against the actual measured
gaps to see if this explains them.

### Honest assessment
This diagnostic has now correctly ruled out 3 real hypotheses with
direct evidence (toggle mechanism -- confirmed working correctly
in isolation; dial computation -- deterministic; dial bootstrap --
real but too small). Each ruling-out was genuine, evidence-based
work, not wasted effort, even though the root cause remains
unfound. The pattern of "checked, genuinely eliminated, moved to
next hypothesis" is the right process -- worth continuing this
exact methodology on fit_svi next session rather than guessing.

### Status: cause still not found, but search space meaningfully
### narrowed. Next concrete step: test fit_svi determinism/variance
### the same way bootstrap_dial_allocation was just tested.
