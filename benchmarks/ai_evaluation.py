import json
import os
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from apps.processing.ai import extract


DOCUMENT_COUNT = int(os.getenv("AI_EVAL_COUNT", "100"))
PROCESSING_TARGET_SECONDS = 30.0
SCHEMA_VALID_TARGET = 99.0

OUTPUT_DIR = Path("benchmark-results/ai")
OUTPUT_FILE = OUTPUT_DIR / "ai-evaluation.json"


def build_document(index: int) -> str:
    income = 4500 + ((index % 15) * 350)
    liabilities = 500 + ((index % 8) * 125)

    employment = (
        "self-employed"
        if index % 10 == 0
        else "employed"
    )

    flags = []

    if index % 17 == 0:
        flags.append("Recent overdraft.")

    if index % 23 == 0:
        flags.append("Late payment reported.")

    return (
        f"Applicant monthly income: ${income}. "
        f"Monthly liabilities: ${liabilities}. "
        f"Employment status: {employment}. "
        + " ".join(flags)
    )


def percentile(values, percentile):
    if not values:
        return 0.0

    values = sorted(values)

    position = (len(values) - 1) * (percentile / 100)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)

    if lower == upper:
        return values[lower]

    fraction = position - lower

    return values[lower] + (
        values[upper] - values[lower]
    ) * fraction


def main():
    if settings.USE_FAKE_AI:
        raise SystemExit(
            "AI evaluation requires USE_FAKE_AI=false."
        )

    if not settings.OPENAI_API_KEY:
        raise SystemExit(
            "OPENAI_API_KEY must be configured."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    valid = 0
    failed = 0
    durations = []
    errors = []

    for index in range(DOCUMENT_COUNT):
        document = build_document(index)

        started = time.perf_counter()

        try:
            result = extract(document)

            # Forces another Pydantic validation pass.
            result.__class__.model_validate(
                result.model_dump()
            )

            valid += 1

        except Exception as exc:
            failed += 1

            errors.append(
                {
                    "document": index,
                    "error": str(exc),
                }
            )

        finally:
            durations.append(
                time.perf_counter() - started
            )

    schema_valid_rate = (
        valid / DOCUMENT_COUNT * 100
        if DOCUMENT_COUNT
        else 0
    )

    results = {
        "documents": DOCUMENT_COUNT,
        "schema_valid": valid,
        "schema_invalid": failed,
        "schema_valid_rate_percent": round(
            schema_valid_rate, 3
        ),
        "average_processing_seconds": round(
            statistics.mean(durations), 3
        ),
        "median_processing_seconds": round(
            statistics.median(durations), 3
        ),
        "p95_processing_seconds": round(
            percentile(durations, 95), 3
        ),
        "max_processing_seconds": round(
            max(durations), 3
        ),
        "targets": {
            "schema_valid_rate_percent": SCHEMA_VALID_TARGET,
            "processing_seconds": PROCESSING_TARGET_SECONDS,
        },
        "errors": errors,
    }

    OUTPUT_FILE.write_text(
        json.dumps(results, indent=2)
    )

    print(json.dumps(results, indent=2))
    print(f"\nResults written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()