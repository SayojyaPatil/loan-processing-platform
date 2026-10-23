
#!/usr/bin/env bash

set -euo pipefail

HOST=${HOST:-http://127.0.0.1:8000}
USERS=${USERS:-50}
SPAWN_RATE=${SPAWN_RATE:-10}
RUN_TIME=${RUN_TIME:-60s}

: "${LOAD_TEST_USERNAME:?Set LOAD_TEST_USERNAME}"
: "${LOAD_TEST_PASSWORD:?Set LOAD_TEST_PASSWORD}"

OUTPUT_DIR="benchmark-results/api/authenticated"
mkdir -p "$OUTPUT_DIR"

echo "Running authenticated loan API benchmark"
echo "Host: $HOST"
echo "Users: $USERS"
echo "Spawn rate: $SPAWN_RATE"
echo "Duration: $RUN_TIME"

locust \
  -f loadtests/locustfile.py \
  --headless \
  --host "$HOST" \
  -u "$USERS" \
  -r "$SPAWN_RATE" \
  -t "$RUN_TIME" \
  --csv "$OUTPUT_DIR/loan-api" \
  --csv-full-history \
  --only-summary

python - "$OUTPUT_DIR/loan-api_stats.csv" <<'PY'
import csv
import sys

with open(sys.argv[1], newline="") as file:
    rows = list(csv.DictReader(file))

total = next(
    row for row in rows
    if row["Name"] == "Aggregated"
)

requests = int(total["Request Count"])
failures = int(total["Failure Count"])
throughput = float(total["Requests/s"])

print("\nAUTHENTICATED BENCHMARK RESULTS")
print(f"Total requests: {requests:,}")
print(f"Failures: {failures}")
print(f"Throughput: {throughput:.2f} requests/sec")

if failures:
    sys.exit("Benchmark recorded request failures")
PY

echo "Authenticated benchmark complete."
echo "Results saved in $OUTPUT_DIR"
