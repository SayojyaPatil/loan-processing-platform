import uuid
from django.db import models
from apps.loans.models import LoanApplication

class Recommendation(models.Model):
    class Decision(models.TextChoices):
        APPROVE='approve','Approve'
        REVIEW='manual_review','Manual Review'
        REJECT='reject','Reject'

    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan=models.OneToOneField(LoanApplication, related_name='recommendation', on_delete=models.CASCADE)
    decision=models.CharField(max_length=30, choices=Decision.choices, db_index=True)
    risk_score=models.PositiveSmallIntegerField()
    debt_to_income=models.DecimalField(max_digits=6, decimal_places=3, null=True)
    monthly_income=models.DecimalField(max_digits=12, decimal_places=2)
    monthly_liabilities=models.DecimalField(max_digits=12, decimal_places=2)
    risk_flags=models.JSONField(default=list)
    reasons=models.JSONField(default=list)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
