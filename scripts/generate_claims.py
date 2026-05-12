#Generate sysnthetic claims data for development and testing
"""Generate synthetic healthcare claims for development and testing."""

import json
import random
from pathlib import Path
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

# --- Constants (fill these in using your domain knowledge) ---

PAYERS = ["Aetna", "Humana", "Cigna"]          # list of insurance companies
PLAN_TYPES = ["PPO", "HMO"]      # PPO, HMO, etc
CLAIM_STATUSES = ["pending", "paid", "denied"]  # what states can a claim be in?

PROCEDURE_CODES = ["99213", "99214", "93000", "71046", "80053", "83036", "36415", "97110", "45378", "27447"] # add 10 common CPT codes you know
DIAGNOSIS_CODES = ["E11.9", "I10", "J06.9", "M54.5", "R07.9", "F41.9", "K21.9", "J45.909", "N39.0", "E78.5"] # add 10 common ICD-10 codes you know

_DENIAL_CODES_DATA = json.loads((Path(__file__).parent.parent / "data/denial_codes.json").read_text())
DENIAL_CODES = list(_DENIAL_CODES_DATA.keys())

PROVIDERS = [
    {"name": "John Smith MD", "npi": "1234567890"},
    {"name": "Emily Johnson DO", "npi": "2345678901"},
    {"name": "Michael Brown NP", "npi": "3456789012"},
    {"name": "Sarah Davis PA", "npi": "4567890123"},
    {"name": "David Wilson MD", "npi": "5678901234"},
]


# --- Helper Functions ---

def generate_claim_id() -> str:
    year = datetime.now().year
    sequence = random.randint(10000, 99999)
    unique = fake.uuid4()[:4].upper()
    return f"CLM-{year}-{sequence}-{unique}"

def generate_date_of_service() -> str:
    """Generate a random date within the last 12 months."""
    return fake.date_between(start_date="-12m", end_date="today").strftime("%Y-%m-%d")

def generate_single_claim() -> dict:
    """Generate one realistic claim record."""
    provider = random.choice(PROVIDERS)
    payer = random.choice(PAYERS)
    plan_type = random.choice(PLAN_TYPES)
    procedure_codes = random.sample(PROCEDURE_CODES, k=random.randint(1, 3))
    diagnosis_codes = random.sample(DIAGNOSIS_CODES, k=random.randint(1, 2))
    status = random.choice(CLAIM_STATUSES)
    billed_amount = round(random.uniform(100, 5000), 2)
    prior_auth_required = random.choice([True, False])
    prior_auth_obtained = prior_auth_required and random.choice([True, False])
    

    claim = {
        "claim_id": generate_claim_id(),
        "patient_id": fake.uuid4()[:8].upper(),
        "provider_name": provider["name"],
        "provider_npi": provider["npi"],
        "payer_name": payer,
        "plan_type": plan_type,
        "date_of_service": generate_date_of_service(),
        "procedure_codes": procedure_codes,
        "diagnosis_codes": diagnosis_codes,
        "billed_amount": billed_amount,
        "claim_status": status,
        "prior_auth_required": prior_auth_required,
        "prior_auth_obtained": prior_auth_obtained,
        "timely_filing_limit_days": random.choice([90, 180, 365]),
    }

    if status == "denied":
        denial_code = random.choice(DENIAL_CODES)
        claim["denial_code"] = denial_code
        claim["denial_reason"] = _DENIAL_CODES_DATA[denial_code]["description"]
    elif status == "paid":
        claim["allowed_amount"] = round(billed_amount * random.uniform(0.6, 0.95), 2)

    return claim


def generate_claims(n: int = 500) -> list:
    """Generate n claims."""
    return [generate_single_claim() for _ in range(n)]

def save_claims(claims: list, filepath: str) -> None:
    """Save claims to JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(claims, indent=2))


# --- Main ---

if __name__ == "__main__":
    claims = generate_claims(500)
    save_claims(claims, "data/claims/sample_claims.json")
    print(f"Generated {len(claims)} claims")