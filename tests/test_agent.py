"""Basic tests for the Healthcare Claims AI Agent."""

import json
import pytest
from pathlib import Path


def test_denial_codes_exist():
    """Denial codes file exists and has content."""
    path = Path("data/denial_codes.json")
    assert path.exists()
    data = json.loads(path.read_text())
    assert len(data) > 0


def test_denial_codes_structure():
    """Each denial code has required fields."""
    path = Path("data/denial_codes.json")
    data = json.loads(path.read_text())
    required_fields = ["code", "category", "description", "common_causes", "resolution"]
    for code, entry in data.items():
        for field in required_fields:
            assert field in entry, f"{code} missing field: {field}"


def test_claims_exist():
    """Sample claims file exists and has 500 records."""
    path = Path("data/claims/sample_claims.json")
    assert path.exists()
    data = json.loads(path.read_text())
    assert len(data) == 500


def test_claims_structure():
    """Each claim has required fields."""
    path = Path("data/claims/sample_claims.json")
    data = json.loads(path.read_text())
    required_fields = [
        "claim_id", "patient_id", "provider_name",
        "payer_name", "claim_status", "billed_amount"
    ]
    for claim in data[:10]:  # test first 10
        for field in required_fields:
            assert field in claim, f"Claim missing field: {field}"


def test_config_loads():
    """Config loads without crashing."""
    from app.config import get_settings
    settings = get_settings()
    assert settings.environment == "local"


def test_claim_model():
    """Claim pydantic model validates correctly."""
    from app.models.claim import Claim
    claim = Claim(
        claim_id="CLM-2026-00001-TEST",
        patient_id="PT-001",
        provider_npi="1234567890",
        provider_name="Test Provider MD",
        date_of_service="2026-01-01",
        procedure_codes=["99213"],
        diagnosis_codes=["I10"],
        billed_amount=250.00,
        plan_type="PPO",
        payer_name="Aetna",
        claim_status="pending"
    )
    assert claim.claim_id == "CLM-2026-00001-TEST"
    assert claim.claim_status == "pending"