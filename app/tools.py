"""Tool definitions and implementations for the Claims AI Agent."""

import json
import logging
import random
from pathlib import Path

from app.models.claim import Claim, ClaimLookupResponse
from app.rag.retriever import retrieve, retrieve_denial_code, format_results_for_claude

logger = logging.getLogger(__name__)

# Load claims data once at startup
CLAIMS_DB_PATH = Path("data/claims/sample_claims.json")
_claims_cache: dict[str, dict] | None = None


def _load_claims() -> dict[str, dict]:
    """Load claims from JSON file into a dict keyed by claim_id.

    Returns:
        Dictionary of claims keyed by claim_id.
    """
    global _claims_cache
    if _claims_cache is None:
        if not CLAIMS_DB_PATH.exists():
            logger.warning("Claims database not found. Run generate_claims.py first.")
            _claims_cache = {}
        else:
            raw = json.loads(CLAIMS_DB_PATH.read_text())
            _claims_cache = {c["claim_id"]: c for c in raw}
            logger.info(f"Loaded {len(_claims_cache)} claims into cache")
    return _claims_cache


# ─────────────────────────────────────────────
# TOOL DEFINITIONS
# These are sent to Claude so it knows what
# tools are available and how to call them
# ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "lookup_claim",
        "description": (
            "Look up a specific insurance claim by its claim ID. "
            "Use this when the provider mentions a specific claim number "
            "or asks about the status of a particular claim."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "The claim ID to look up (e.g. CLM-2026-12345-AB1C)"
                }
            },
            "required": ["claim_id"]
        }
    },
    {
        "name": "search_policy_docs",
        "description": (
            "Search the knowledge base for relevant policy information, "
            "denial code explanations, coverage rules, or prior authorization "
            "requirements. Use this when the provider asks about policies, "
            "coverage, denial reasons, or appeal guidance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant policy documents"
                },
                "filter_type": {
                    "type": "string",
                    "enum": ["denial_code", "policy_document"],
                    "description": "Optional filter to search only denial codes or policy documents"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_denial_explanation",
        "description": (
            "Get a detailed explanation of a specific denial code. "
            "Use this when you know the exact denial code and need "
            "to explain it to the provider."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "denial_code": {
                    "type": "string",
                    "description": "The denial code to explain (e.g. CO-4, PR-1, OA-23)"
                }
            },
            "required": ["denial_code"]
        }
    },
    {
        "name": "generate_appeal_letter",
        "description": (
            "Generate a professional appeal letter for a denied claim. "
            "Use this when the provider asks for help appealing a denial."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "The claim ID to generate an appeal letter for"
                },
                "additional_context": {
                    "type": "string",
                    "description": "Any additional clinical context or notes to include in the appeal"
                }
            },
            "required": ["claim_id"]
        }
    }
]


# ─────────────────────────────────────────────
# TOOL IMPLEMENTATIONS
# The actual Python functions that execute
# when Claude calls a tool
# ─────────────────────────────────────────────

def lookup_claim(claim_id: str) -> dict:
    """Look up a claim by ID and return its details.

    Args:
        claim_id: The claim ID to look up.

    Returns:
        Dictionary with found status, claim data, and message.
    """
    claims = _load_claims()

    # Try exact match first
    if claim_id in claims:
        claim_data = claims[claim_id]
        return ClaimLookupResponse(
            found=True,
            claim=Claim(**claim_data),
            message=f"Claim {claim_id} found successfully."
        ).model_dump()

    # Try case-insensitive partial match
    claim_id_upper = claim_id.upper()
    for key, value in claims.items():
        if claim_id_upper in key.upper():
            return ClaimLookupResponse(
                found=True,
                claim=Claim(**value),
                message=f"Claim {key} found."
            ).model_dump()

    return ClaimLookupResponse(
        found=False,
        claim=None,
        message=f"No claim found with ID '{claim_id}'. Please verify the claim number."
    ).model_dump()


def search_policy_docs(query: str, filter_type: str | None = None) -> dict:
    """Search ChromaDB for relevant policy documents.

    Args:
        query: Search query string.
        filter_type: Optional filter for document type.

    Returns:
        Dictionary with results and formatted context.
    """
    results = retrieve(query=query, n_results=3, filter_type=filter_type)
    formatted = format_results_for_claude(results)

    return {
        "query": query,
        "results_count": len(results),
        "context": formatted
    }


def get_denial_explanation(denial_code: str) -> dict:
    """Get detailed explanation for a specific denial code.

    Args:
        denial_code: The denial code string (e.g. CO-4).

    Returns:
        Dictionary with denial code details or not found message.
    """
    result = retrieve_denial_code(denial_code.upper())

    if result:
        return {
            "found": True,
            "denial_code": denial_code.upper(),
            "explanation": result.document,
            "metadata": result.metadata
        }

    return {
        "found": False,
        "denial_code": denial_code,
        "explanation": f"Denial code '{denial_code}' not found in knowledge base."
    }


def generate_appeal_letter(claim_id: str, additional_context: str = "") -> dict:
    """Generate a professional appeal letter for a denied claim.

    Args:
        claim_id: The claim ID to generate appeal letter for.
        additional_context: Additional clinical notes or context.

    Returns:
        Dictionary with appeal letter text or error message.
    """
    # First look up the claim
    claim_response = lookup_claim(claim_id)

    if not claim_response["found"]:
        return {
            "success": False,
            "message": f"Cannot generate appeal letter: {claim_response['message']}"
        }

    claim = claim_response["claim"]

    if claim["claim_status"] != "denied":
        return {
            "success": False,
            "message": f"Claim {claim_id} is not denied (status: {claim['claim_status']}). Appeal letters are only for denied claims."
        }

    # Get denial code context
    denial_explanation = ""
    if claim.get("denial_code"):
        denial_result = get_denial_explanation(claim["denial_code"])
        denial_explanation = denial_result.get("explanation", "")

    # Build appeal letter
    letter = f"""
APPEAL LETTER FOR DENIED CLAIM

Date: {__import__('datetime').date.today().strftime('%B %d, %Y')}

Re: Appeal for Claim {claim['claim_id']}
Patient ID: {claim['patient_id']}
Provider: {claim['provider_name']} (NPI: {claim['provider_npi']})
Date of Service: {claim['date_of_service']}
Procedure Code(s): {', '.join(claim['procedure_codes'])}
Diagnosis Code(s): {', '.join(claim['diagnosis_codes'])}
Billed Amount: ${claim['billed_amount']:,.2f}
Denial Code: {claim.get('denial_code', 'N/A')}

Dear Appeals Department,

We are writing to formally appeal the denial of the above-referenced claim.

REASON FOR DENIAL:
{claim.get('denial_reason', 'Not specified')}

GROUNDS FOR APPEAL:
The services provided were medically necessary and appropriate for the 
patient's diagnosis. We respectfully request reconsideration of this claim 
based on the following:

1. The procedure(s) performed ({', '.join(claim['procedure_codes'])}) were 
   clinically indicated for the documented diagnosis ({', '.join(claim['diagnosis_codes'])}).

2. All services were rendered within the plan's coverage guidelines.

3. {additional_context if additional_context else 'Supporting clinical documentation is available upon request.'}

REQUESTED ACTION:
We respectfully request that you reverse the denial and process this claim 
for payment. Please review the attached clinical documentation supporting 
the medical necessity of these services.

If you require additional information, please contact our billing department.

Sincerely,

{claim['provider_name']}
NPI: {claim['provider_npi']}
    """.strip()

    return {
        "success": True,
        "claim_id": claim_id,
        "appeal_letter": letter
    }


# ─────────────────────────────────────────────
# TOOL DISPATCHER
# Routes Claude's tool_use calls to the
# correct Python function
# ─────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name and return result as string.

    Args:
        tool_name: Name of the tool to execute.
        tool_input: Input parameters for the tool.

    Returns:
        JSON string result of the tool execution.
    """
    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

    tool_map = {
        "lookup_claim": lookup_claim,
        "search_policy_docs": search_policy_docs,
        "get_denial_explanation": get_denial_explanation,
        "generate_appeal_letter": generate_appeal_letter,
    }

    if tool_name not in tool_map:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = tool_map[tool_name](**tool_input)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    # Quick test
    print("Testing tools...\n")

    # Test claim lookup
    claims = _load_claims()
    sample_id = list(claims.keys())[0]

    print(f"1. Looking up claim: {sample_id}")
    result = lookup_claim(sample_id)
    print(json.dumps(result, indent=2))

    print("\n2. Searching policy docs for 'prior authorization'")
    result = search_policy_docs("prior authorization requirements")
    print(f"Found {result['results_count']} results")
    print(result['context'][:300])

    print("\n3. Getting denial explanation for CO-4")
    result = get_denial_explanation("CO-4")
    print(result['explanation'][:300])