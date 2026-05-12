Here it is — copy everything below and paste into your `README.md`:

```markdown
# Healthcare Claims AI Agent

An AI-powered agent that helps medical providers navigate insurance claims, understand denials, and generate appeal letters using Claude AI and RAG architecture.

## Demo

```
Provider: "Why was claim #4821 denied?"
Agent: "Claim #4821 was denied with code CO-4 (modifier issue).
        The procedure 99213 requires modifier -25 for same-day billing.
        Here are the steps to correct and resubmit..."
```

## Architecture

```
FastAPI REST API
      ↓
Claude AI Agent (Orchestrator)
      ↓
Tools: lookup_claim | search_policy_docs | get_denial_explanation | generate_appeal_letter
      ↓
ChromaDB (RAG) + Synthetic Claims Database
```

## Features

- **Claim Lookup** — retrieve claim status, denial codes, and billing details
- **Denial Explanation** — plain English explanations of CO, PR, OA denial codes
- **Policy Search** — semantic search over insurance policy documents
- **Appeal Letters** — auto-generated professional appeal letters from claim data
- **Conversation Memory** — maintains context across multi-turn conversations
- **Session Management** — multiple concurrent provider sessions

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Orchestration | Claude claude-sonnet-4-5 (Anthropic) |
| RAG / Vector DB | ChromaDB |
| API Framework | FastAPI |
| Containerization | Docker |
| Cloud | AWS (ECS + S3) |
| Data | Synthetic HIPAA-safe claims |

## Project Structure

```
healthcare-claims-ai-agent/
├── app/
│   ├── main.py              # FastAPI endpoints
│   ├── agent.py             # Claude orchestration loop
│   ├── tools.py             # Tool definitions and implementations
│   ├── config.py            # Settings management
│   ├── rag/
│   │   ├── ingest.py        # Document ingestion pipeline
│   │   └── retriever.py     # Semantic search
│   └── models/
│       └── claim.py         # Pydantic data models
├── data/
│   ├── denial_codes.json    # 25 CO/PR/OA denial codes
│   └── claims/              # 500 synthetic claims
├── scripts/
│   └── generate_claims.py
├── docker/
│   └── Dockerfile
└── docker-compose.yml
```

## Quick Start

### Prerequisites
- Python 3.11+
- Docker
- Anthropic API key

### Local Setup

```bash
# Clone the repo
git clone https://github.com/rajusubbaprojects/healthcare-claims-ai-agent.git
cd healthcare-claims-ai-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# Generate synthetic claims data
python scripts/generate_claims.py

# Ingest knowledge base
python -m app.rag.ingest

# Start the API
python -m uvicorn app.main:app --reload --port 8000
```

### Docker

```bash
docker build -f docker/Dockerfile -t claims-agent .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=your_key claims-agent
```

## API Reference

### Health Check

```
GET /health
```

### Chat with Agent

```json
POST /chat
{
  "message": "Why was claim CLM-2026-12345 denied?",
  "session_id": "optional-for-conversation-continuity"
}
```

### Example Queries

```bash
# Explain a denial code
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is denial code CO-4?"}'

# Look up a specific claim
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Look up claim CLM-2026-23363-817E"}'

# Generate an appeal letter
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Write an appeal letter for claim CLM-2026-23363-817E"}'
```

## Data & HIPAA Compliance

This project uses **synthetic data only** — no real patient records.

- Claims generated using Faker with realistic healthcare domain structure
- System designed for HIPAA-eligible AWS infrastructure (S3, ECS)
- No PII stored in vector database
- API keys managed via environment variables

## Agentic Pattern

Claude doesn't just answer — it decides which tools to call based on the query.

Multi-step example:

```
"Why was claim 4821 denied and how do I appeal?"
  1. lookup_claim(4821)            ← gets claim data
  2. get_denial_explanation(CO-4)  ← explains the code
  3. generate_appeal_letter(4821)  ← drafts the letter
  4. Claude synthesizes all three into one response
```

## Author

**Raju Subba** — BI Engineer transitioning to ML/AI Engineer
Specializing in Healthcare AI

[GitHub](https://github.com/rajusubbaprojects) | [LinkedIn](https://linkedin.com/in/your-profile)
```

---

Paste that in, save, then commit and push.