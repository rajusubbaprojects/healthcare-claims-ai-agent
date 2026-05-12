"""Core agent orchestration loop for the Healthcare Claims AI Agent."""

import json
import logging
from anthropic import Anthropic

from app.config import get_settings
from app.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Anthropic client once at startup
client = Anthropic(api_key=settings.anthropic_api_key)

# System prompt that defines agent behavior
SYSTEM_PROMPT = """You are a Healthcare Claims AI Agent designed to help 
medical providers navigate insurance claims, understand claim denials, 
and prepare appeal letters.

You have access to the following tools:
- lookup_claim: Look up a specific claim by ID
- search_policy_docs: Search insurance policy and denial code knowledge base
- get_denial_explanation: Get detailed explanation of a specific denial code
- generate_appeal_letter: Generate a professional appeal letter for a denied claim

Guidelines:
1. Always look up the claim first when a claim ID is mentioned
2. Search policy docs when asked about coverage or authorization rules
3. Be specific and actionable in your responses
4. Use plain English to explain complex insurance terminology
5. Always cite the denial code when explaining a denial
6. Recommend next steps after explaining a denial
7. Be empathetic — providers are often frustrated with the claims process

You only answer questions related to healthcare insurance claims.
For unrelated questions, politely redirect to claims topics.
"""


def run_agent(
    user_message: str,
    conversation_history: list[dict] | None = None
) -> tuple[str, list[dict]]:
    """Run the agent for a single user message.

    Handles the full agentic loop — sends message to Claude,
    executes any tool calls, and returns the final response.

    Args:
        user_message: The provider's question or request.
        conversation_history: Previous messages in the conversation.

    Returns:
        Tuple of (agent_response, updated_conversation_history).
    """
    if conversation_history is None:
        conversation_history = []

    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    logger.info(f"Processing message: {user_message[:100]}...")

    # Agentic loop — keeps running until Claude gives a final text response
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=conversation_history
        )

        logger.info(f"Claude stop reason: {response.stop_reason}")

        # Claude wants to use a tool
        if response.stop_reason == "tool_use":
            # Add Claude's response to history
            conversation_history.append({
                "role": "assistant",
                "content": response.content
            })

            # Execute all tool calls Claude requested
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"Executing tool: {block.name}")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Add tool results to history and loop again
            conversation_history.append({
                "role": "user",
                "content": tool_results
            })

        # Claude has a final answer
        elif response.stop_reason == "end_turn":
            # Extract text response
            final_response = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_response += block.text

            # Add final response to history
            conversation_history.append({
                "role": "assistant",
                "content": final_response
            })

            logger.info("Agent completed response")
            return final_response, conversation_history

        # Unexpected stop reason
        else:
            logger.error(f"Unexpected stop reason: {response.stop_reason}")
            return "I encountered an unexpected error. Please try again.", conversation_history


def chat(session_id: str | None = None) -> None:
    """Run an interactive chat session in the terminal.

    Args:
        session_id: Optional session identifier for logging.
    """
    print("Healthcare Claims AI Agent")
    print("=" * 40)
    print("Ask me about insurance claims, denials, or appeals.")
    print("Type 'quit' to exit.\n")

    conversation_history = []

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        try:
            response, conversation_history = run_agent(
                user_message=user_input,
                conversation_history=conversation_history
            )
            print(f"\nAgent: {response}\n")

        except Exception as e:
            logger.error(f"Agent error: {e}")
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    chat()