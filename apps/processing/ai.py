import json, re
from django.conf import settings
from .schemas import ExtractedLoanData

SYSTEM_PROMPT='Extract underwriting facts from supplied loan-document text. Do not invent unsupported facts.'

def _money(pattern: str, text: str, default: float=0.0) -> float:
    m=re.search(pattern, text, re.I)
    return float(m.group(1).replace(',','')) if m else default

def fake_extract(text: str) -> ExtractedLoanData:
    income=_money(r'(?:monthly income|income)\s*[:$]?\s*\$?([\d,]+(?:\.\d+)?)', text, 6500)
    liabilities=_money(r'(?:monthly liabilities|liabilities|debt payments)\s*[:$]?\s*\$?([\d,]+(?:\.\d+)?)', text, 1500)
    lower=text.lower()
    status='unemployed' if 'unemployed' in lower else ('self_employed' if 'self-employed' in lower or 'self employed' in lower else 'employed')
    flags=[]
    if 'overdraft' in lower: flags.append('recent_overdraft')
    if 'late payment' in lower: flags.append('late_payment')
    if 'bankruptcy' in lower: flags.append('bankruptcy_mention')
    return ExtractedLoanData(monthly_income=income, employment_status=status, employer='Demo Employer' if status=='employed' else None, monthly_liabilities=liabilities, risk_flags=flags, confidence=0.96)

def extract(text: str) -> ExtractedLoanData:
    if settings.USE_FAKE_AI or not settings.OPENAI_API_KEY:
        return fake_extract(text)
    from openai import OpenAI
    client=OpenAI(api_key=settings.OPENAI_API_KEY)
    schema=ExtractedLoanData.model_json_schema()
    response=client.responses.create(
        model=settings.OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,
        input=text,
        text={'format': {'type':'json_schema','name':'loan_document_extraction','schema':schema,'strict':False}},
    )
    return ExtractedLoanData.model_validate_json(response.output_text)
