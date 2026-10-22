# AI-Powered Loan Processing Platform

An asynchronous backend platform for loan-document processing, structured data extraction, underwriting recommendations, and approval workflows.

## Tech Stack

- Django
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Pydantic
- Docker
- OpenAI API
- Locust

## Architecture

```text
Client
  ↓
Django REST Framework
  ↓
PostgreSQL
  ↓
Loan Submission
  ↓
Redis Queue
  ↓
Celery Worker
  ↓
OpenAI Document Extraction
  ↓
Pydantic Validation
  ↓
Underwriting Engine
  ↓
Approve / Manual Review / Reject
```

The platform separates synchronous API operations from longer-running AI and document-processing workloads.

## Core Workflow

1. Create a loan application through the REST API.
2. Attach loan documents.
3. Submit the application for processing.
4. Redis queues the processing task.
5. Celery performs document analysis asynchronously.
6. OpenAI extracts structured financial and risk information.
7. Pydantic validates the extracted output.
8. The underwriting engine calculates debt-to-income ratio and risk indicators.
9. The platform generates an approval, rejection, or manual-review recommendation.
10. Processing state and underwriting results are persisted in PostgreSQL.

## Features

- Loan and document CRUD APIs
- Asynchronous document processing with Celery and Redis
- OpenAI-powered structured document extraction
- Pydantic validation of model outputs
- Automated underwriting recommendations
- Debt-to-income calculations
- Risk scoring and manual-review flags
- PostgreSQL persistence and targeted indexing
- Processing-job tracking
- Swagger / OpenAPI documentation
- Dockerized multi-service development environment
- Synthetic data generation
- API load testing with Locust
- PostgreSQL indexed vs. unindexed performance benchmarking

## AI Extraction

The project supports two processing modes.

### Mock Mode

```env
USE_FAKE_AI=true
```

Mock mode uses deterministic structured data for local development without requiring OpenAI API calls.

### OpenAI Mode

```env
USE_FAKE_AI=false
OPENAI_API_KEY=your_api_key
```

OpenAI responses are validated with Pydantic before being used by the underwriting workflow.

Extracted fields include:

- Monthly income
- Employment information
- Monthly liabilities
- Confidence scores
- Risk indicators
- Loan recommendation inputs

## Performance Results

### OpenAI Extraction Evaluation

The OpenAI extraction pipeline was evaluated across **100 synthetic loan documents**.

Measured results:

```text
Documents evaluated:       100
Schema-valid responses:    100 / 100
Schema-valid rate:         100%

Average processing time:   1.72 seconds
Median processing time:    1.54 seconds
P95 processing time:       2.69 seconds
Maximum processing time:   8.65 seconds
```

The evaluation produced **0 schema-validation failures**.

The benchmark can be reproduced with:

```bash
USE_FAKE_AI=false AI_EVAL_COUNT=100 python benchmarks/ai_evaluation.py
```

Results are written to:

```text
benchmark-results/ai/
```

## API Load Testing

Core REST endpoints were tested with Locust under:

```text
Concurrent users: 50
Spawn rate:       10 users / second
Duration:         60 seconds
```

Measured results:

```text
Total requests:          17,392
Request failures:        0
Aggregate throughput:    ~297 requests / second
Worst endpoint P95:      24 ms
```

Endpoint-level P95 latency:

```text
GET  /api/loans/               24 ms
GET  /api/processing-jobs/     19 ms
POST /api/loans/               15 ms
```

Run the benchmark with:

```bash
./benchmarks/api_benchmark.sh
```

Results are written to:

```text
benchmark-results/api/
```

## PostgreSQL Performance

Representative loan and document queries were benchmarked against equivalent unindexed baselines using PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)`.

Measured results:

```text
Loan status lookup:
Indexed median:     0.027 ms
Unindexed median:   2.763 ms
Improvement:        99.02%

Applicant lookup:
Indexed median:     0.012 ms
Unindexed median:   0.4935 ms
Improvement:        97.57%

Document lookup:
Indexed median:     0.015 ms
Unindexed median:   0.339 ms
Improvement:        95.58%
```

Summary:

```text
Average improvement:  97.39%
Best improvement:     99.02%
Worst improvement:    95.58%
```

The benchmark uses temporary indexed and unindexed copies of the same dataset so the application's production indexes are not modified.

Run:

```bash
python benchmarks/database_benchmark.py
```

Results are written to:

```text
benchmark-results/database/
```

## Running Locally

### 1. Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create the environment configuration

```bash
cp .env.example .env
```

Example local configuration:

```env
DJANGO_SECRET_KEY=dev-secret-change-me
DJANGO_DEBUG=true

POSTGRES_DB=loans
POSTGRES_USER=loans
POSTGRES_PASSWORD=loans
POSTGRES_HOST=localhost
POSTGRES_PORT=5433

REDIS_URL=redis://localhost:6379/0

OPENAI_API_KEY=
USE_FAKE_AI=true
```

### 4. Start PostgreSQL and Redis

```bash
docker compose up -d db redis
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Run Django

```bash
python manage.py runserver
```

or:

```bash
python -m gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 \
  --workers 4 \
  --threads 4
```

### 7. Start Celery

```bash
celery -A config worker -l info --pool=solo
```

## API Documentation

Swagger documentation is available at:

```text
http://127.0.0.1:8000/api/docs/
```

OpenAPI schema:

```text
http://127.0.0.1:8000/api/schema/
```

## Example Workflow

### Create a Loan

```bash
curl -X POST http://127.0.0.1:8000/api/loans/ \
  -H 'Content-Type: application/json' \
  -d '{
    "applicant_name": "Alex Morgan",
    "applicant_email": "alex@example.com",
    "requested_amount": "50000.00",
    "purpose": "debt_consolidation"
  }'
```

### Add a Document

```bash
curl -X POST http://127.0.0.1:8000/api/documents/ \
  -H 'Content-Type: application/json' \
  -d '{
    "loan": "LOAN_UUID",
    "kind": "paystub",
    "filename": "paystub.txt",
    "text_content": "Monthly income: $8000. Monthly liabilities: $1200. Employment status: employed."
  }'
```

### Submit the Loan

```bash
curl -X POST \
  http://127.0.0.1:8000/api/loans/LOAN_UUID/submit/
```

### Check Processing Status

```text
GET /api/processing-jobs/
GET /api/processing-jobs/{id}/
```

### Retrieve Underwriting Recommendation

```text
GET /api/recommendations/?loan=LOAN_UUID
```

## Generate Synthetic Data

Synthetic loan applications can be generated for development and benchmark preparation.

```bash
python manage.py seed_loans --count 1000
```

The record count is configurable:

```bash
python manage.py seed_loans --count 5000
```

Generated applications are synthetic test data and are not intended to represent production usage.

## API Endpoints

### Loans

```text
GET    /api/loans/
POST   /api/loans/
GET    /api/loans/{id}/
PUT    /api/loans/{id}/
PATCH  /api/loans/{id}/
DELETE /api/loans/{id}/
POST   /api/loans/{id}/submit/
```

### Documents

```text
GET    /api/documents/
POST   /api/documents/
GET    /api/documents/{id}/
PUT    /api/documents/{id}/
PATCH  /api/documents/{id}/
DELETE /api/documents/{id}/
```

### Processing Jobs

```text
GET /api/processing-jobs/
GET /api/processing-jobs/{id}/
```

### Recommendations

```text
GET /api/recommendations/
GET /api/recommendations/{id}/
```

## Reliability Features

- Redis-backed task queue
- Asynchronous Celery workers
- Processing-job state tracking
- Celery retries
- Retry backoff and jitter
- Late task acknowledgements
- Task timeouts
- Pydantic output validation
- Database transactions
- Idempotent recommendation updates
- Indexed PostgreSQL lookup fields
- Separation of synchronous API and background worker processes

## Testing

Run:

```bash
python -m pytest -q
```

The project includes tests for structured-output validation and underwriting behavior.

## Project Structure

```text
loan-processing-platform/
├── apps/
│   ├── documents/
│   ├── loans/
│   ├── processing/
│   └── underwriting/
├── benchmarks/
│   ├── ai_evaluation.py
│   ├── api_benchmark.sh
│   ├── check_api_results.py
│   └── database_benchmark.py
├── benchmark-results/
├── config/
├── loadtests/
│   └── locustfile.py
├── tests/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── pytest.ini
├── README.md
└── requirements.txt
```

## Benchmark Summary

| Metric | Result |
|---|---:|
| OpenAI schema-valid responses | **100% (100/100)** |
| OpenAI average processing time | **1.72s** |
| OpenAI P95 processing time | **2.69s** |
| API load-test requests | **17,392** |
| API failures | **0** |
| Worst endpoint API P95 | **24ms** |
| Aggregate API throughput | **~297 req/s** |
| PostgreSQL average lookup improvement | **97.39%** |
| PostgreSQL worst tested improvement | **95.58%** |

## Potential Enhancements

- PDF upload and parsing
- OCR integration
- S3-compatible object storage
- Role-based authentication
- File validation and malware scanning
- Celery dead-letter queues
- Prometheus metrics
- OpenTelemetry tracing
- CI/CD pipelines
- Cloud deployment
- Operations dashboard