
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.loans.models import LoanApplication
from apps.documents.models import LoanDocument
from apps.underwriting.models import Recommendation
from apps.underwriting.service import evaluate

from .models import ProcessingJob
from .ai import extract
from .schemas import ExtractedLoanData


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
)
def process_loan(self, job_id: str):
    task_id = self.request.id or ""

    # Claim the job while holding the row lock.
    with transaction.atomic():
        job = (
            ProcessingJob.objects
            .select_for_update()
            .select_related("loan")
            .get(pk=job_id)
        )

        if job.status == ProcessingJob.Status.SUCCEEDED:
            return {
                "job_id": str(job.id),
                "status": "already_completed",
            }

        if job.status == ProcessingJob.Status.FAILED:
            return {
                "job_id": str(job.id),
                "status": "already_failed",
            }

        if job.status == ProcessingJob.Status.RUNNING:
            return {
                "job_id": str(job.id),
                "status": "already_running",
            }

        job.status = ProcessingJob.Status.RUNNING
        job.started_at = timezone.now()
        job.completed_at = None
        job.attempts += 1
        job.celery_task_id = task_id
        job.error = ""

        job.save(
            update_fields=[
                "status",
                "started_at",
                "completed_at",
                "attempts",
                "celery_task_id",
                "error",
            ]
        )

        loan = job.loan

        LoanApplication.objects.filter(pk=loan.pk).update(
            status=LoanApplication.Status.PROCESSING
        )

    try:
        docs = list(
            LoanDocument.objects.filter(loan=loan)
        )

        if not docs:
            raise ValueError(
                "At least one document is required before processing"
            )

        extracted = []

        for doc in docs:
            parsed = extract(
                doc.text_content or doc.filename
            )

            doc.extracted_data = parsed.model_dump()
            doc.processed = True
            doc.processed_at = timezone.now()

            doc.save(
                update_fields=[
                    "extracted_data",
                    "processed",
                    "processed_at",
                ]
            )

            extracted.append(parsed)

        income = max(
            (item.monthly_income for item in extracted),
            default=0,
        )

        liabilities = max(
            (item.monthly_liabilities for item in extracted),
            default=0,
        )

        flags = sorted({
            flag
            for item in extracted
            for flag in item.risk_flags
        })

        confidence = min(
            (item.confidence for item in extracted),
            default=0,
        )

        employment = next(
            (
                item.employment_status
                for item in extracted
                if item.employment_status != "other"
            ),
            "other",
        )

        combined = ExtractedLoanData(
            monthly_income=income,
            employment_status=employment,
            employer=None,
            monthly_liabilities=liabilities,
            risk_flags=flags,
            confidence=confidence,
        )

        result = evaluate(
            combined,
            loan.requested_amount,
        )

        new_status = {
            "approve": LoanApplication.Status.APPROVED,
            "reject": LoanApplication.Status.REJECTED,
            "manual_review": LoanApplication.Status.REVIEW,
        }[result.decision]

        # Commit the recommendation and final statuses together.
        with transaction.atomic():
            locked_job = (
                ProcessingJob.objects
                .select_for_update()
                .get(pk=job.pk)
            )

            if locked_job.status != ProcessingJob.Status.RUNNING:
                return {
                    "job_id": str(job.id),
                    "status": "state_changed",
                }

            Recommendation.objects.update_or_create(
                loan=loan,
                defaults={
                    "decision": result.decision,
                    "risk_score": result.risk_score,
                    "debt_to_income": result.debt_to_income,
                    "monthly_income": income,
                    "monthly_liabilities": liabilities,
                    "risk_flags": result.risk_flags,
                    "reasons": result.reasons,
                },
            )

            LoanApplication.objects.filter(
                pk=loan.pk
            ).update(status=new_status)

            locked_job.status = ProcessingJob.Status.SUCCEEDED
            locked_job.completed_at = timezone.now()
            locked_job.error = ""

            locked_job.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "error",
                ]
            )

        return {
            "job_id": str(job.id),
            "decision": result.decision,
            "risk_score": result.risk_score,
        }

    except Exception as exc:
        final_attempt = (
            self.request.retries >= self.max_retries
        )

        with transaction.atomic():
            locked_job = (
                ProcessingJob.objects
                .select_for_update()
                .get(pk=job.pk)
            )

            if locked_job.status == ProcessingJob.Status.RUNNING:
                if final_attempt:
                    locked_job.status = ProcessingJob.Status.FAILED
                    locked_job.error = type(exc).__name__
                    locked_job.completed_at = timezone.now()

                    locked_job.save(
                        update_fields=[
                            "status",
                            "error",
                            "completed_at",
                        ]
                    )

                    LoanApplication.objects.filter(
                        pk=loan.pk
                    ).update(
                        status=LoanApplication.Status.REVIEW
                    )

                else:
                    locked_job.status = ProcessingJob.Status.QUEUED
                    locked_job.save(
                        update_fields=["status"]
                    )

        # Allow Celery's autoretry mechanism to handle the error.
        raise
