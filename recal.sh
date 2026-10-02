#!/bin/bash
# Weekly: keep the live proxy's 1m history, re-run the backtests (rewrites gate-*.json by the same
# pre-registered rule), snapshot the scorecard, and commit + push.
set -euo pipefail
cd "$(dirname "$0")"
export DYLD_FALLBACK_LIBRARY_PATH="$HOME/.venvs/market-ml/lib/python3.11/site-packages/torch/lib"
PY="$HOME/.venvs/market-ml/bin/python"
$PY archive.py > /dev/null
$PY backtest.py > /dev/null
$PY agent.py --scorecard > results/scorecard.txt
GIT=/usr/local/bin/git
$GIT add gate-*.json results data/bars data/windows-*.jsonl data/evals-*.jsonl
$GIT diff --cached --quiet || $GIT commit -q -m "Weekly recalibration $(date +%F)"
$GIT push -q origin HEAD 2>&1 || echo "push failed" >&2
