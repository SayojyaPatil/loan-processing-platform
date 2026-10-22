#!/usr/bin/env bash
set -euo pipefail
HOST=${HOST:-http://localhost:8000}
USERS=${USERS:-50}
SPAWN_RATE=${SPAWN_RATE:-10}
RUN_TIME=${RUN_TIME:-60s}
mkdir -p benchmark-results
locust -f loadtests/locustfile.py --headless --host "$HOST" -u "$USERS" -r "$SPAWN_RATE" -t "$RUN_TIME" --csv benchmark-results/loan-api
printf '\nResults written to benchmark-results/loan-api_stats.csv\n'
