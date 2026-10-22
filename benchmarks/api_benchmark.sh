#!/usr/bin/env bash

set -euo pipefail

HOST=${HOST:-http://127.0.0.1:8000}
USERS=${USERS:-50}
SPAWN_RATE=${SPAWN_RATE:-10}
RUN_TIME=${RUN_TIME:-60s}

mkdir -p benchmark-results/api

locust \
  -f loadtests/locustfile.py \
  --headless \
  --host "$HOST" \
  -u "$USERS" \
  -r "$SPAWN_RATE" \
  -t "$RUN_TIME" \
  --csv benchmark-results/api/loan-api

python benchmarks/check_api_results.py

echo "API benchmark complete."