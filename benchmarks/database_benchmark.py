import json
import os
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.db import connection


ITERATIONS = int(os.getenv("DB_BENCHMARK_ITERATIONS", "30"))

OUTPUT_DIR = Path("benchmark-results/database")
OUTPUT_FILE = OUTPUT_DIR / "database-benchmark.json"


def percentile(values, pct):
    values = sorted(values)

    if not values:
        return 0.0

    position = (len(values) - 1) * pct / 100
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)

    if lower == upper:
        return values[lower]

    fraction = position - lower

    return values[lower] + (
        values[upper] - values[lower]
    ) * fraction


def execution_time(cursor, query, params=None):
    cursor.execute(
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query,
        params or [],
    )

    result = cursor.fetchone()[0][0]

    return float(result["Execution Time"])


def measure(cursor, query, params=None):
    # Warm-up runs
    for _ in range(5):
        execution_time(cursor, query, params)

    times = []

    for _ in range(ITERATIONS):
        times.append(
            execution_time(cursor, query, params)
        )

    return {
        "median_ms": statistics.median(times),
        "p95_ms": percentile(times, 95),
        "min_ms": min(times),
        "max_ms": max(times),
    }


def compare(cursor, indexed_query, unindexed_query, params=None):
    indexed = measure(cursor, indexed_query, params)
    unindexed = measure(cursor, unindexed_query, params)

    improvement = (
        (unindexed["median_ms"] - indexed["median_ms"])
        / unindexed["median_ms"]
        * 100
        if unindexed["median_ms"] > 0
        else 0
    )

    return {
        "indexed_median_ms": round(indexed["median_ms"], 4),
        "indexed_p95_ms": round(indexed["p95_ms"], 4),
        "unindexed_median_ms": round(unindexed["median_ms"], 4),
        "unindexed_p95_ms": round(unindexed["p95_ms"], 4),
        "improvement_percent": round(improvement, 2),
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}

    with connection.cursor() as cursor:

        print("Creating temporary benchmark tables...")

        # Same data, separate indexed and unindexed copies.
        cursor.execute("""
            CREATE TEMP TABLE bench_loans_indexed AS
            SELECT *
            FROM loans_loanapplication
        """)

        cursor.execute("""
            CREATE TEMP TABLE bench_loans_unindexed AS
            SELECT *
            FROM loans_loanapplication
        """)

        cursor.execute("""
            CREATE TEMP TABLE bench_documents_indexed AS
            SELECT *
            FROM documents_loandocument
        """)

        cursor.execute("""
            CREATE TEMP TABLE bench_documents_unindexed AS
            SELECT *
            FROM documents_loandocument
        """)

        # Add indexes only to indexed copies.
        cursor.execute("""
            CREATE INDEX bench_loan_status_created_idx
            ON bench_loans_indexed(status, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX bench_loan_email_created_idx
            ON bench_loans_indexed(applicant_email, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX bench_doc_loan_processed_idx
            ON bench_documents_indexed(loan_id, processed)
        """)

        cursor.execute(
            "ANALYZE bench_loans_indexed"
        )
        cursor.execute(
            "ANALYZE bench_loans_unindexed"
        )
        cursor.execute(
            "ANALYZE bench_documents_indexed"
        )
        cursor.execute(
            "ANALYZE bench_documents_unindexed"
        )

        # Get a real email for exact-match benchmark.
        cursor.execute("""
            SELECT applicant_email
            FROM loans_loanapplication
            LIMIT 1
        """)

        email = cursor.fetchone()[0]

        # Get a real loan with a document.
        cursor.execute("""
            SELECT loan_id
            FROM documents_loandocument
            LIMIT 1
        """)

        loan_row = cursor.fetchone()
        loan_id = loan_row[0] if loan_row else None

        print("Benchmarking status lookup...")

        results["loan_status_lookup"] = compare(
            cursor,
            """
            SELECT id, applicant_email, requested_amount, status
            FROM bench_loans_indexed
            WHERE status = 'draft'
            ORDER BY created_at DESC
            LIMIT 50
            """,
            """
            SELECT id, applicant_email, requested_amount, status
            FROM bench_loans_unindexed
            WHERE status = 'draft'
            ORDER BY created_at DESC
            LIMIT 50
            """,
        )

        print("Benchmarking applicant email lookup...")

        results["loan_email_lookup"] = compare(
            cursor,
            """
            SELECT id, applicant_email, requested_amount, status
            FROM bench_loans_indexed
            WHERE applicant_email = %s
            ORDER BY created_at DESC
            LIMIT 50
            """,
            """
            SELECT id, applicant_email, requested_amount, status
            FROM bench_loans_unindexed
            WHERE applicant_email = %s
            ORDER BY created_at DESC
            LIMIT 50
            """,
            [email],
        )

        if loan_id:
            print("Benchmarking document lookup...")

            results["document_lookup"] = compare(
                cursor,
                """
                SELECT id, loan_id, processed, created_at
                FROM bench_documents_indexed
                WHERE loan_id = %s
                  AND processed = false
                LIMIT 50
                """,
                """
                SELECT id, loan_id, processed, created_at
                FROM bench_documents_unindexed
                WHERE loan_id = %s
                  AND processed = false
                LIMIT 50
                """,
                [loan_id],
            )

    improvements = [
        result["improvement_percent"]
        for result in results.values()
    ]

    results["summary"] = {
        "queries_tested": len(improvements),
        "average_improvement_percent": round(
            statistics.mean(improvements), 2
        ),
        "best_improvement_percent": round(
            max(improvements), 2
        ),
        "worst_improvement_percent": round(
            min(improvements), 2
        ),
    }

    OUTPUT_FILE.write_text(
        json.dumps(results, indent=2)
    )

    print("\nPOSTGRESQL BENCHMARK RESULTS")
    print("=" * 70)

    for name, result in results.items():
        if name == "summary":
            continue

        print(f"\n{name}")
        print(
            f"  Indexed median:   "
            f"{result['indexed_median_ms']} ms"
        )
        print(
            f"  Unindexed median: "
            f"{result['unindexed_median_ms']} ms"
        )
        print(
            f"  Improvement:      "
            f"{result['improvement_percent']}%"
        )

    print("\nSUMMARY")
    print(
        f"Average improvement: "
        f"{results['summary']['average_improvement_percent']}%"
    )
    print(
        f"Best improvement:    "
        f"{results['summary']['best_improvement_percent']}%"
    )
    print(
        f"Worst improvement:   "
        f"{results['summary']['worst_improvement_percent']}%"
    )

    print(
        f"\nResults written to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()