#!/bin/bash
# Waits for IB Gateway to be logged in and ready before starting
# the poller -- Gateway itself auto-launches on boot, but needs
# your manual login first, so this script waits patiently rather
# than failing immediately.

cd ~/tradingbot/engine
source ~/anaconda3/etc/profile.d/conda.sh
conda activate tradingbot

echo "Waiting for IB Gateway to be ready..."
while true; do
    python3 -c "
from ib_insync import IB
ib = IB()
try:
    ib.connect('127.0.0.1', 4002, clientId=99, timeout=3)
    ib.disconnect()
    exit(0)
except Exception:
    exit(1)
" && break
    sleep 10
done

echo "Gateway ready -- starting poller"
nohup python3 -u live_value_poller.py > live_poller_log.txt 2>&1 &
