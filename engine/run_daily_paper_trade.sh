#!/bin/bash
# Daily scheduled run of the paper trading loop. Requires IB
# Gateway to already be running and logged in (paper trading mode)
# -- this script does NOT start Gateway itself, since that
# requires an interactive login. Logs every run for real visibility
# into what happened, rather than running silently and hoping.

LOGFILE=~/tradingbot/engine/paper_trade_log.txt
DATE=$(date +"%Y-%m-%d %H:%M:%S")

echo "===== Run started: $DATE =====" >> "$LOGFILE"

cd ~/tradingbot/engine
source ~/anaconda3/etc/profile.d/conda.sh
conda activate tradingbot

# Real, live run -- NOT dry_run, since the whole point of
# scheduling is to actually keep the portfolio rebalanced
python3 -c "
import sys
sys.path.insert(0, '.')
import json
import pandas as pd
import os
from paper_trading_loop import PaperTradingLoop

DATA_DIR = os.path.expanduser('~/tradingbot/engine/histdata')
px = pd.read_parquet(os.path.join(DATA_DIR, 'bt_prices.parquet'))
px.index = pd.to_datetime(px.index).tz_localize(None)

with open(os.path.join(DATA_DIR, 'final_equity_universe.json')) as f:
    universe = json.load(f)

loop = PaperTradingLoop()
if loop.connect():
    loop.run_once(px, universe, dry_run=False)
    loop.ib.disconnect()
else:
    print('Connection failed -- is IB Gateway running and logged in?')
" >> "$LOGFILE" 2>&1

echo "===== Run finished: $(date +"%Y-%m-%d %H:%M:%S") =====" >> "$LOGFILE"
echo "" >> "$LOGFILE"
