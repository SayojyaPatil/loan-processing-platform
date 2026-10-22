# Loan Processing Platform

A portfolio-grade backend for asynchronous loan-document processing and underwriting recommendations.

## Stack
Django, Django REST Framework, PostgreSQL, Redis, Celery, Pydantic, Docker, OpenAI Responses API, Locust.

## Architecture

1. Client creates a loan through `POST /api/loans/`.
2. Client adds one or more loan documents through `POST /api/documents/`.
3. `POST /api/loans/{id}/submit/` creates a `ProcessingJob` and immediately returns HTTP 202.
4. Celery consumes the job from Redis outside the API request path.
5. Document text is extracted into a Pydantic schema.
6. The underwriting service calculates DTI, risk score, reasons, and approve/manual-review/reject recommendation.
7. Job, loan, documents, and recommendation states are persisted in PostgreSQL.

The project defaults to a deterministic fake AI extractor (`USE_FAKE_AI=true`) so it can be developed and load-tested without API cost. Set `USE_FAKE_AI=false` and add `OPENAI_API_KEY` to use the OpenAI Responses API with JSON-schema structured output, followed by application-side Pydantic validation. OpenAI currently recommends JSON Schema structured outputs for supported models. See the official API docs.

## Run

```bash
cp .env.example .env
docker compose up --build
```

API: `http://localhost:8000/api/`
Swagger: `http://localhost:8000/api/docs/`

## Example flow

Create a loan:

```bash
curl -X POST http://localhost:8000/api/loans/ \
  -H 'Content-Type: application/json' \
  -d '{"applicant_name":"Alex Morgan","applicant_email":"alex@example.com","requested_amount":"50000.00","purpose":"debt_consolidation"}'
```

Create a document using the returned loan UUID:

```bash
curl -X POST http://localhost:8000/api/documents/ \
  -H 'Content-Type: application/json' \
  -d '{"loan":"LOAN_UUID","kind":"paystub","filename":"paystub.txt","text_content":"Monthly income: $8000. Monthly liabilities: $1200. Employment status: employed."}'
```

Submit:

```bash
curl -X POST http://localhost:8000/api/loans/LOAN_UUID/submit/
```

Poll `GET /api/processing-jobs/JOB_UUID/` and then query `GET /api/recommendations/?loan=LOAN_UUID`.

## Generate 5,000 simulated applications

```bash
docker compose exec web python manage.py seed_loans --count 5000
```

This creates 5,000 loan rows and 5,000 associated simulated documents. It supports the *dataset scale* claim only; it does not by itself prove throughput or latency.

## Load test core APIs

```bash
./benchmark.sh
```

Defaults: 50 concurrent Locust users, 10 users/second ramp, 60 seconds. Override with:

```bash
USERS=100 SPAWN_RATE=20 RUN_TIME=3m ./benchmark.sh
```

Inspect `benchmark-results/loan-api_stats.csv` for request count, failures, average latency, and percentile latency. Only claim `<200 ms P95` on a resume after the measured P95 for the relevant endpoints is actually below 200 ms on a documented environment.

## Validate the 99%+ schema-valid metric

The fake extractor is deterministic and Pydantic-valid by construction, so it should **not** be used to claim an AI schema-valid rate. For the resume metric, build a labeled evaluation set (for example 200–500 representative documents), run it with `USE_FAKE_AI=false`, count responses that pass `ExtractedLoanData` validation, and report:

`schema_valid_rate = valid_responses / total_model_responses * 100`

## Validate the 60% query improvement metric

Use PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` on representative loan/document lookups with the checked-in indexes, then compare against the same queries after dropping the target indexes in a disposable benchmark database. Record median/P95 execution time over repeated runs. Do not use the 60% claim unless your measurement supports it.

## Useful endpoints

- `GET/POST /api/loans/`
- `GET/PATCH/DELETE /api/loans/{id}/`
- `POST /api/loans/{id}/submit/`
- `GET/POST /api/documents/`
- `GET /api/processing-jobs/`
- `GET /api/recommendations/`
- `GET /api/docs/`

## Reliability features already included

Celery retries with exponential backoff and jitter; late acknowledgement; worker-loss rejection; soft/hard task timeouts; durable processing-job state; idempotent recommendation upsert; transaction around final decision state; indexed status and lookup columns; API/worker separation.

## Good next upgrades

Object storage (S3) for real PDFs, antivirus/file validation, authentication/permissions, document OCR/parser abstraction, idempotency keys on submission, Celery dead-letter handling, Prometheus/OpenTelemetry, CI, AWS deployment, and a React dashboard.
