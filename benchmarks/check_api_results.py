import csv
from pathlib import Path

RESULT_FILE = Path("benchmark-results/api/loan-api_stats.csv")
P95_TARGET_MS = 200.0


def main():
    if not RESULT_FILE.exists():
        raise SystemExit(f"Missing benchmark file: {RESULT_FILE}")

    rows = []

    with RESULT_FILE.open(newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row.get("Name") == "Aggregated":
                continue

            request_count = int(float(row.get("Request Count", 0) or 0))

            if request_count == 0:
                continue

            p95 = float(row.get("95%", 0) or 0)
            failures = int(float(row.get("Failure Count", 0) or 0))

            rows.append(
                {
                    "endpoint": row.get("Name"),
                    "requests": request_count,
                    "failures": failures,
                    "p95_ms": p95,
                    "passes_200ms_target": p95 < P95_TARGET_MS,
                }
            )

    print("\nAPI PERFORMANCE RESULTS")
    print("-" * 80)

    for row in rows:
        print(
            f"{row['endpoint']:<35} "
            f"requests={row['requests']:<6} "
            f"failures={row['failures']:<4} "
            f"P95={row['p95_ms']:.2f} ms "
            f"target={'PASS' if row['passes_200ms_target'] else 'FAIL'}"
        )

    measured = [r for r in rows if r["p95_ms"] > 0]

    if measured:
        worst_p95 = max(r["p95_ms"] for r in measured)

        print("-" * 80)
        print(f"Worst endpoint P95: {worst_p95:.2f} ms")
        print(f"Target: < {P95_TARGET_MS:.0f} ms")


if __name__ == "__main__":
    main()