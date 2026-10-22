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

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=30, retry_jitter=True, max_retries=3)
def process_loan(self, job_id: str):
    job=ProcessingJob.objects.select_related('loan').get(id=job_id)
    job.status=ProcessingJob.Status.RUNNING
    job.started_at=timezone.now(); job.attempts += 1; job.celery_task_id=self.request.id or ''
    job.save(update_fields=['status','started_at','attempts','celery_task_id'])
    loan=job.loan
    LoanApplication.objects.filter(id=loan.id).update(status=LoanApplication.Status.PROCESSING)
    try:
        docs=list(LoanDocument.objects.filter(loan=loan))
        if not docs: raise ValueError('At least one document is required before processing')
        extracted=[]
        for doc in docs:
            parsed=extract(doc.text_content or doc.filename)
            doc.extracted_data=parsed.model_dump()
            doc.processed=True; doc.processed_at=timezone.now()
            doc.save(update_fields=['extracted_data','processed','processed_at'])
            extracted.append(parsed)

        income=max((d.monthly_income for d in extracted), default=0)
        liabilities=max((d.monthly_liabilities for d in extracted), default=0)
        flags=sorted({flag for d in extracted for flag in d.risk_flags})
        confidence=min((d.confidence for d in extracted), default=0)
        employment=next((d.employment_status for d in extracted if d.employment_status!='other'),'other')
        combined=ExtractedLoanData(monthly_income=income, employment_status=employment, employer=None, monthly_liabilities=liabilities, risk_flags=flags, confidence=confidence)
        result=evaluate(combined, loan.requested_amount)

        with transaction.atomic():
            Recommendation.objects.update_or_create(loan=loan, defaults={
                'decision':result.decision,'risk_score':result.risk_score,'debt_to_income':result.debt_to_income,
                'monthly_income':income,'monthly_liabilities':liabilities,'risk_flags':result.risk_flags,'reasons':result.reasons,
            })
            new_status={'approve':LoanApplication.Status.APPROVED,'reject':LoanApplication.Status.REJECTED,'manual_review':LoanApplication.Status.REVIEW}[result.decision]
            LoanApplication.objects.filter(id=loan.id).update(status=new_status)
            job.status=ProcessingJob.Status.SUCCEEDED; job.completed_at=timezone.now(); job.error=''; job.save(update_fields=['status','completed_at','error'])
        return {'job_id':str(job.id),'decision':result.decision,'risk_score':result.risk_score}
    except Exception as exc:
        job.status=ProcessingJob.Status.FAILED; job.error=str(exc); job.completed_at=timezone.now(); job.save(update_fields=['status','error','completed_at'])
        LoanApplication.objects.filter(id=loan.id).update(status=LoanApplication.Status.REVIEW)
        raise
