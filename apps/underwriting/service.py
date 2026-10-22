from decimal import Decimal
from dataclasses import dataclass
from apps.processing.schemas import ExtractedLoanData

@dataclass
class UnderwritingResult:
    decision: str
    risk_score: int
    debt_to_income: Decimal | None
    reasons: list[str]
    risk_flags: list[str]

def evaluate(data: ExtractedLoanData, requested_amount: Decimal) -> UnderwritingResult:
    income=Decimal(str(data.monthly_income))
    liabilities=Decimal(str(data.monthly_liabilities))
    dti=(liabilities/income) if income > 0 else None
    score=0
    reasons=[]
    flags=list(data.risk_flags)

    if income <= 0:
        score += 70; reasons.append('No verified monthly income')
    if data.employment_status == 'unemployed':
        score += 35; reasons.append('Applicant is currently unemployed')
    if dti is not None and dti > Decimal('0.50'):
        score += 35; reasons.append('Debt-to-income ratio exceeds 50%')
    elif dti is not None and dti > Decimal('0.40'):
        score += 20; reasons.append('Debt-to-income ratio exceeds 40%')
    if requested_amount > income * Decimal('24'):
        score += 20; reasons.append('Requested amount is high relative to verified income')
    score += min(len(flags) * 8, 24)
    score=min(score,100)

    if score >= 65: decision='reject'
    elif score >= 30 or data.confidence < 0.85: decision='manual_review'
    else: decision='approve'
    if not reasons: reasons.append('Income, liabilities, and risk signals are within configured thresholds')
    return UnderwritingResult(decision, score, dti, reasons, flags)
