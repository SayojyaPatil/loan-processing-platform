from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

class ExtractedLoanData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    monthly_income: float = Field(ge=0, le=1_000_000)
    employment_status: Literal['employed','self_employed','unemployed','retired','other']
    employer: str | None = Field(default=None, max_length=200)
    monthly_liabilities: float = Field(ge=0, le=1_000_000)
    risk_flags: list[str] = Field(default_factory=list, max_length=20)
    confidence: float = Field(ge=0, le=1)
