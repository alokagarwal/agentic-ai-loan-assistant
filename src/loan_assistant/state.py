from typing import Annotated, TypedDict
import operator 

class LoanState(TypedDict):
    application_id: str
    documents: list[str]
    loan_amount: float
    extracted_data: dict
    affordability: dict
    policy_check: dict
    recommendation: str
    audit_log: Annotated[list[str], operator.add]