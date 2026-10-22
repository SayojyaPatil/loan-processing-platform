from decimal import Decimal
from apps.processing.schemas import ExtractedLoanData
from apps.underwriting.service import evaluate

def test_low_risk_application_is_approved():
    data=ExtractedLoanData(monthly_income=8000, employment_status='employed', employer='Acme', monthly_liabilities=1200, risk_flags=[], confidence=.98)
    result=evaluate(data, Decimal('50000'))
    assert result.decision == 'approve'
    assert result.risk_score < 30

def test_high_dti_goes_to_review_or_reject():
    data=ExtractedLoanData(monthly_income=4000, employment_status='employed', employer='Acme', monthly_liabilities=2300, risk_flags=['late_payment'], confidence=.95)
    result=evaluate(data, Decimal('70000'))
    assert result.decision in {'manual_review','reject'}
    assert result.debt_to_income > Decimal('.50')
