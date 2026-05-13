"""Data models for healthcare insurance claims."""

from pydantic import BaseModel
from typing import Optional


class Claim(BaseModel):
    """Represents a single healthcare insurance claim.

    Attributes:
        claim_id: Unique claim identifier.
        patient_id: Unique patient identifier.
        provider_npi: Provider NPI number.
        provider_name: Name of the provider.
        date_of_service: Date service was rendered.
        procedure_codes: List of CPT procedure codes.
        diagnosis_codes: List of ICD-10 diagnosis codes.
        billed_amount: Amount billed by provider.
        allowed_amount: Amount allowed by payer.
        plan_type: Insurance plan type (PPO, HMO, EPO).
        payer_name: Name of the insurance payer.
        claim_status: Current claim status (denied, pending, paid).
        denial_code: Denial reason code if claim was denied.
        denial_reason: Human readable denial reason.
        prior_auth_required: Whether prior auth was required.
        prior_auth_obtained: Whether prior auth was obtained.
        timely_filing_limit_days: Days allowed to file claim.
    """

    claim_id: str
    patient_id: str
    provider_npi: str
    provider_name: str
    date_of_service: str
    procedure_codes: list[str]
    diagnosis_codes: list[str]
    billed_amount: float
    allowed_amount: Optional[float] = None
    plan_type: str
    payer_name: str
    claim_status: str
    denial_code: Optional[str] = None
    denial_reason: Optional[str] = None
    prior_auth_required: bool = False
    prior_auth_obtained: bool = False
    timely_filing_limit_days: int = 90


class ClaimLookupResponse(BaseModel):
    """Response returned after a claim lookup.

    Attributes:
        found: Whether the claim was found.
        claim: The claim object if found, None otherwise.
        message: Human readable result message.
    """

    found: bool
    claim: Optional[Claim] = None
    message: str