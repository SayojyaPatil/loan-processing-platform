import pytest
from pydantic import ValidationError
from apps.processing.schemas import ExtractedLoanData

def test_schema_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        ExtractedLoanData(monthly_income=5000, employment_status='employed', monthly_liabilities=1000, confidence=.9, unknown='x')

def test_schema_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        ExtractedLoanData(monthly_income=5000, employment_status='employed', monthly_liabilities=1000, confidence=2)
