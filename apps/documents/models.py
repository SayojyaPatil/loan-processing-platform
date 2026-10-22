import uuid
from django.db import models
from apps.loans.models import LoanApplication

class LoanDocument(models.Model):
    class Kind(models.TextChoices):
        PAYSTUB='paystub','Pay Stub'
        BANK='bank_statement','Bank Statement'
        W2='w2','W-2'
        ID='id','Identification'
        OTHER='other','Other'

    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan=models.ForeignKey(LoanApplication, related_name='documents', on_delete=models.CASCADE, db_index=True)
    kind=models.CharField(max_length=30, choices=Kind.choices)
    filename=models.CharField(max_length=255)
    text_content=models.TextField(blank=True)
    extracted_data=models.JSONField(default=dict, blank=True)
    processed=models.BooleanField(default=False, db_index=True)
    created_at=models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at=models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes=[models.Index(fields=['loan','processed'], name='doc_loan_processed_idx')]
        ordering=['-created_at']
