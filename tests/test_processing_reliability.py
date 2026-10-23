
"""Celery processing reliability regression tests."""

import pytest
from django.contrib.auth import get_user_model

from apps.loans.models import LoanApplication
from apps.documents.models import LoanDocument
from apps.processing.models import ProcessingJob
from apps.processing.tasks import process_loan
from apps.processing.ai import fake_extract
from apps.underwriting.models import Recommendation


@pytest.fixture
def processing_job(db):
    user = get_user_model().objects.create_user(
        username="processing_test_user",
        password="test-only-password",
    )

    loan = LoanApplication.objects.create(
        owner=user,
        applicant_name="Synthetic Applicant",
        applicant_email="synthetic@example.test",
        requested_amount="15000.00",
        purpose="Automated reliability test",
        status=LoanApplication.Status.SUBMITTED,
    )

    LoanDocument.objects.create(
        loan=loan,
        kind=LoanDocument.Kind.PAYSTUB,
        filename="sample.txt",
        text_content=(
            "Monthly income: 6500. "
            "Monthly liabilities: 1200. "
            "Employment status: employed."
        ),
    )

    return ProcessingJob.objects.create(loan=loan)


def run_task(job):
    # Execute locally and synchronously through Celery.
    # This does not publish anything to Redis.
    return process_loan.apply(
        args=(str(job.pk),),
        throw=False,
    )


def test_successful_processing(processing_job, monkeypatch):
    monkeypatch.setattr(
        "apps.processing.tasks.extract",
        fake_extract,
    )

    result = run_task(processing_job)

    processing_job.refresh_from_db()
    processing_job.loan.refresh_from_db()

    assert result.successful()
    assert processing_job.status == ProcessingJob.Status.SUCCEEDED
    assert processing_job.attempts == 1
    assert processing_job.error == ""
    assert processing_job.completed_at is not None
    assert processing_job.loan.status in (
        LoanApplication.Status.APPROVED,
        LoanApplication.Status.REJECTED,
        LoanApplication.Status.REVIEW,
    )
    assert Recommendation.objects.filter(
        loan=processing_job.loan
    ).count() == 1


def test_completed_job_is_not_reprocessed(
    processing_job,
    monkeypatch,
):
    monkeypatch.setattr(
        "apps.processing.tasks.extract",
        fake_extract,
    )

    first = run_task(processing_job)
    assert first.successful()

    def unexpected_extract(_text):
        raise AssertionError(
            "Completed job must not run extraction again"
        )

    monkeypatch.setattr(
        "apps.processing.tasks.extract",
        unexpected_extract,
    )

    second = run_task(processing_job)

    processing_job.refresh_from_db()

    assert second.successful()
    assert second.result["status"] == "already_completed"
    assert processing_job.attempts == 1
    assert Recommendation.objects.filter(
        loan=processing_job.loan
    ).count() == 1


def test_running_job_is_not_claimed_again(
    processing_job,
    monkeypatch,
):
    processing_job.status = ProcessingJob.Status.RUNNING
    processing_job.save(update_fields=["status"])

    def unexpected_extract(_text):
        raise AssertionError(
            "Running job must not be processed twice"
        )

    monkeypatch.setattr(
        "apps.processing.tasks.extract",
        unexpected_extract,
    )

    result = run_task(processing_job)

    processing_job.refresh_from_db()

    assert result.successful()
    assert result.result["status"] == "already_running"
    assert processing_job.attempts == 0


def test_temporary_failure_recovers_after_retry(
    processing_job,
    monkeypatch,
):
    calls = {"count": 0}

    def flaky_extract(text):
        calls["count"] += 1

        if calls["count"] == 1:
            raise RuntimeError("Temporary extraction failure")

        return fake_extract(text)

    monkeypatch.setattr(
        "apps.processing.tasks.extract",
        flaky_extract,
    )

    result = run_task(processing_job)

    processing_job.refresh_from_db()

    assert result.successful()
    assert calls["count"] == 2
    assert processing_job.attempts == 2
    assert processing_job.status == ProcessingJob.Status.SUCCEEDED
    assert Recommendation.objects.filter(
        loan=processing_job.loan
    ).count() == 1


def test_retry_exhaustion_marks_failure(
    processing_job,
    monkeypatch,
):
    sensitive_message = (
        "Synthetic applicant confidential information"
    )

    def always_fail(_text):
        raise RuntimeError(sensitive_message)

    monkeypatch.setattr(
        "apps.processing.tasks.extract",
        always_fail,
    )

    result = run_task(processing_job)

    processing_job.refresh_from_db()
    processing_job.loan.refresh_from_db()

    assert result.failed()
    assert processing_job.attempts == 4
    assert processing_job.status == ProcessingJob.Status.FAILED
    assert processing_job.loan.status == LoanApplication.Status.REVIEW
    assert processing_job.error == "RuntimeError"
    assert sensitive_message not in processing_job.error
    assert processing_job.completed_at is not None
    assert Recommendation.objects.filter(
        loan=processing_job.loan
    ).count() == 0
