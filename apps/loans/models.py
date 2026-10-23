import uuid
from django.db import models

class LoanApplication(models.Model):
    class Status(models.TextChoices):
        DRAFT='draft','Draft'
        SUBMITTED='submitted','Submitted'
        PROCESSING='processing','Processing'
        REVIEW='review','Manual Review'
        APPROVED='approved','Approved'
        REJECTED='rejected','Rejected'

    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner=models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='loan_applications', null=True, blank=True)
    applicant_name=models.CharField(max_length=200)
    applicant_email=models.EmailField(db_index=True)
    requested_amount=models.DecimalField(max_digits=12, decimal_places=2)
    purpose=models.CharField(max_length=255)
    status=models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_at=models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        indexes=[
            models.Index(fields=['status','-created_at'], name='loan_status_created_idx'),
            models.Index(fields=['applicant_email','-created_at'], name='loan_email_created_idx'),
        ]
        ordering=['-created_at']
