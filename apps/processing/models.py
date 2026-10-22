import uuid
from django.db import models
from apps.loans.models import LoanApplication

class ProcessingJob(models.Model):
    class Status(models.TextChoices):
        QUEUED='queued','Queued'
        RUNNING='running','Running'
        SUCCEEDED='succeeded','Succeeded'
        FAILED='failed','Failed'

    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan=models.ForeignKey(LoanApplication, related_name='processing_jobs', on_delete=models.CASCADE)
    status=models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    celery_task_id=models.CharField(max_length=255, blank=True, db_index=True)
    attempts=models.PositiveIntegerField(default=0)
    error=models.TextField(blank=True)
    started_at=models.DateTimeField(null=True, blank=True)
    completed_at=models.DateTimeField(null=True, blank=True)
    created_at=models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes=[models.Index(fields=['loan','-created_at'], name='job_loan_created_idx')]
        ordering=['-created_at']
