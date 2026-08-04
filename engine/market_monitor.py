"""
Unified global market monitor.
Same logic for all markets -- one dial, one threshold system.
"""
import os, sys, time, json, pytz, schedule
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
ET = pytz.timezone("America/New_York")
DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
CONFIG   = os.path.expanduser("~/tradingbot/config")

SESSIONS = {
    "Asia":    {"open": 20, "close": 6,
                "tickers": ["EWJ","FXI","EWH","EWT","EWY","ES=F","NQ=F"]},
    "Europe":  {"open": 3,  "close": 12,
                "tickers": ["VGK","EWG","EWU","EUFN","ES=F"]},
    "US":      {"open": 9,  "close": 16,
                "tickers": ["SPY","QQQ","EEM","SCHF","^VIX","HYG","LQD"]},
    "Futures": {"open": 18, "close": 17,
                "tickers": ["ES=F","NQ=F","GC=F","CL=F","ZB=F","DX-Y.NYB"]},
}

THRESHOLDS = {
    "YELLOW": 0.12,
    "ORANGE": 0.20,
    "RED":    0.28,
    "CRISIS": 0.85,
}

ALERT_COOLDOWN = 1800


class MarketMonitor:

    def __init__(self):
        self.baseline_dial = self._load_baseline()
        self.current_dial  = self.baseline_dial
        self.last_alert    = {}
        self.alert_history = []
        print(f"Monitor initialized. Baseline dial: {self.baseline_dial:.2f}")

    def _load_baseline(self):
        try:
            stab = pd.read_parquet(
                os.path.join(DATA_DIR, "stability.parquet"))
            return float(stab["stability_risk"].dropna().iloc[-1])
        except Exception:
            return 0.40

    def _save_baseline(self, dial):
        path = os.path.join(CONFIG, "monitor_baseline.json")
        with open(path, "w") as f:
            json.dump({"baseline": dial,
                       "timestamp": datetime.now(ET).isoformat()}, f)
        self.baseline_dial = dial

    def active_sessions(self):
        now  = datetime.now(ET)
        hour = now.hour
        active = []
        for name, s in SESSIONS.items():
            o, c = s["open"], s["close"]
            if o > c:
                if hour >= o or hour < c:
                    active.append(name)
            else:
                if o <= hour < c:
                    active.append(name)
        return active if active else ["Futures"]

    def active_tickers(self):
        sessions = self.active_sessions()
        tickers  = set()
        for s in sessions:
            tickers.update(SESSIONS[s]["tickers"])
        tickers.update(SESSIONS["Futures"]["tickers"])
        return list(tickers)

    def compute_fast_dial(self):
        tickers = self.active_tickers()
        score   = 0.0
        total_w = 0.0
        try:
            data = yf.download(tickers, period="2d",
                               progress=False,
                               auto_adjust=True)["Close"]
            if isinstance(data, pd.Series):
                data = data.to_frame(name=tickers[0])
            for ticker in tickers:
                if ticker not in data.columns:
                    continue
                s = data[ticker].dropna()
                if len(s) < 2:
                    continue
                move = float(s.iloc[-1] / s.iloc[-2] - 1)
                if ticker in ["SPY","QQQ","EEM","SCHF","EWJ","FXI",
                               "EWH","EWT","EWY","VGK","EWG","EWU",
                               "EUFN","ES=F","NQ=F"]:
                    score += min(max(-move / 0.05, 0), 1.0) * 0.30
                    total_w += 0.30
                elif ticker == "^VIX":
                    score += min(max(move / 0.20, 0), 1.0) * 0.40
                    total_w += 0.40
                elif ticker == "HYG":
                    score += min(max(-move / 0.03, 0), 1.0) * 0.30
                    total_w += 0.30
                elif ticker in ["GC=F","GLD"]:
                    score += min(max(move / 0.02, 0), 1.0) * 0.15
                    total_w += 0.15
                elif ticker == "DX-Y.NYB":
                    score += min(max(move / 0.01, 0), 1.0) * 0.15
                    total_w += 0.15
        except Exception as e:
            print(f"Fast dial error: {e}")
            return self.current_dial
        if total_w == 0:
            return self.current_dial
        raw     = score / total_w
        blended = 0.7 * self.current_dial + 0.3 * raw
        return float(np.clip(blended, 0, 1))

    def check_thresholds(self, dial):
        move     = dial - self.baseline_dial
        sessions = self.active_sessions()
        if dial >= THRESHOLDS["CRISIS"]:
            self._alert("RED", dial, move, sessions,
                        "Dial crossed 0.85 — CRISIS MODE")
            return "CRISIS"
        if move >= THRESHOLDS["RED"]:
            self._alert("RED", dial, move, sessions,
                        "Emergency rebalance required")
            return "RED"
        elif move >= THRESHOLDS["ORANGE"]:
            self._alert("ORANGE", dial, move, sessions,
                        "De-risk to stress config")
            return "ORANGE"
        elif move >= THRESHOLDS["YELLOW"]:
            self._alert("YELLOW", dial, move, sessions,
                        "Monitor closely")
            return "YELLOW"
        return "OK"

    def _alert(self, level, dial, move, sessions, action):
        now = time.time()
        if level in self.last_alert:
            if now - self.last_alert[level] < ALERT_COOLDOWN:
                return
        self.last_alert[level] = now
        icons = {"YELLOW":"⚠️","ORANGE":"🟠","RED":"🔴","CRISIS":"🆘"}
        icon  = icons.get(level, "📊")
        msg   = (
            f"{icon} *{level} ALERT*\n"
            f"Dial: {dial:.2f} (baseline {self.baseline_dial:.2f}, "
            f"move +{move:.2f})\n"
            f"Open: {', '.join(sessions)}\n"
            f"Action: {action}\n"
            f"Time: {datetime.now(ET).strftime('%a %b %d %H:%M ET')}"
        )
        if level in ("RED","CRISIS"):
            msg += "\n\n*Reply CONFIRM to rebalance or HOLD to skip*"
        try:
            from slack_utils import send_slack
            send_slack(msg)
        except Exception as e:
            print(f"Slack error: {e}")
        print(f"{icon} {level}: dial={dial:.2f} move=+{move:.2f}")

    def fast_check(self):
        dial = self.compute_fast_dial()
        self.current_dial = dial
        status = self.check_thresholds(dial)
        print(f"  [{datetime.now(ET).strftime('%H:%M')}] "
              f"dial={dial:.2f} status={status} "
              f"sessions={self.active_sessions()}", flush=True)

    def session_check(self):
        self.fast_check()

    def daily_close(self):
        print(f"\nDaily close {datetime.now(ET).strftime('%Y-%m-%d')}...")
        try:
            stab = pd.read_parquet(
                os.path.join(DATA_DIR, "stability.parquet"))
            dial = float(stab["stability_risk"].dropna().iloc[-1])
            self._save_baseline(dial)
            self.current_dial = dial
            from stability_index import risk_multiplier
            mult = risk_multiplier(dial)
            try:
                from slack_utils import send_slack
                send_slack(
                    f"📊 *Daily Close* "
                    f"{datetime.now(ET).strftime('%a %b %d')}\n"
                    f"Dial: {dial:.2f} → risk mult {mult:.2f}\n"
                    f"Baseline updated.")
            except Exception:
                pass
            print(f"  Dial: {dial:.2f} | mult: {mult:.2f}")
        except Exception as e:
            print(f"  Daily close error: {e}")
        self._sync_schwab()

    def weekly_optimization(self):
        print(f"\nWeekly optimization "
              f"{datetime.now(ET).strftime('%Y-%m-%d %H:%M')}...")
        try:
            from portfolio_engine import compute_allocation
            result = compute_allocation(method="svi")
            self._save_baseline(result["dial"])
            self.current_dial = result["dial"]
            print(f"  Done. Dial: {result['dial']:.2f}")
        except Exception as e:
            print(f"  Weekly error: {e}")

    def _sync_schwab(self):
        try:
            import schwab, json
            client = schwab.auth.client_from_token_file(
                token_path=os.path.expanduser(
                    "~/tradingbot/config/schwab_tokens.json"),
                api_key=os.getenv("SCHWAB_CLIENT_ID"),
                app_secret=os.getenv("SCHWAB_CLIENT_SECRET"))
            cfg = json.load(open(os.path.expanduser(
                "~/tradingbot/config/bot_config.json")))
            h = cfg.get("schwab_account_hash","")
            if not h:
                return
            resp = client.get_account(
                h, fields=[client.Account.Fields.POSITIONS])
            positions = (resp.json()
                        .get("securitiesAccount",{})
                        .get("positions",[]))
            portfolio = [
                {"symbol": p["instrument"]["symbol"],
                 "shares": p["longQuantity"],
                 "cost_basis": p["averagePrice"],
                 "source": "schwab"}
                for p in positions
                if p.get("longQuantity",0) > 0]
            with open(os.path.expanduser(
                    "~/tradingbot/config/portfolio.json"),"w") as f:
                json.dump(portfolio, f, indent=2)
            print(f"  Schwab: {len(portfolio)} positions")
        except Exception as e:
            print(f"  Schwab sync failed: {e}")

    def run(self):
        self.running = True
        print("=" * 60)
        print("MARKET TERMINAL — GLOBAL MONITOR")
        print("=" * 60)
        print(f"Baseline: {self.baseline_dial:.2f}")
        print(f"Thresholds: Y={THRESHOLDS['YELLOW']} "
              f"O={THRESHOLDS['ORANGE']} R={THRESHOLDS['RED']}")
        print(f"Watching: US, Asia, Europe, Futures 24/7")
        print("=" * 60)

        schedule.every(5).minutes.do(self.fast_check)
        schedule.every(30).minutes.do(self.session_check)
        for day in ["monday","tuesday","wednesday","thursday","friday"]:
            getattr(schedule.every(), day).at("16:05").do(
                self.daily_close)
        schedule.every().sunday.at("20:00").do(
            self.weekly_optimization)

        self.fast_check()
        while self.running:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    monitor = MarketMonitor()
    monitor.run()
