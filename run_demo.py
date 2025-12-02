# run_demo.py
import asyncio

from a2a_utils import CustomerServiceA2AClient

# Router / Orchestrator entrypoint
ROUTER_URL = "http://localhost:9200"
client = CustomerServiceA2AClient()


# ---------------------------------------------------------------------------
# 5 Required Test Scenarios (assignment wording)
# ---------------------------------------------------------------------------

async def simple_query() -> None:
    """Simple Query: single-agent, straightforward MCP call."""
    print("=== Simple Query ===")
    user_text = "Get customer information for ID 5"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def coordinated_query() -> None:
    """Coordinated Query: data fetch + support response."""
    print("=== Coordinated Query ===")
    user_text = "I'm customer 12345 and need help upgrading my account"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def complex_query() -> None:
    """Complex Query: customers with open tickets."""
    print("=== Complex Query ===")
    user_text = "Show me all active customers who have open tickets"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def escalation_query() -> None:
    """Escalation: billing issue that should be treated as urgent."""
    print("=== Escalation ===")
    user_text = "I've been charged twice, please refund immediately!"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def multi_intent_query() -> None:
    """Multi-Intent: update profile + show history in one request."""
    print("=== Multi-Intent ===")
    user_text = "My customer ID is 4. Update my email to new@email.com and show my ticket history"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


# ---------------------------------------------------------------------------
# 3 A2A Orchestration Scenarios
# ---------------------------------------------------------------------------

async def scenario_task_allocation() -> None:
    """
    Scenario 1: Task Allocation

    Router receives the query, fetches customer context, and routes
    handling to the appropriate specialist path.
    """
    print("=== Scenario 1: Task Allocation ===")
    user_text = "I need help with my account, my customer ID is 12345"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def scenario_negotiation_escalation() -> None:
    """
    Scenario 2: Negotiation / Escalation

    Router detects cancellation + billing issues and coordinates between
    Data and Support agents to form a coherent response.
    """
    print("=== Scenario 2: Negotiation/Escalation ===")
    user_text = "I want to cancel my subscription but I'm having billing issues"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def scenario_multi_step_coordination() -> None:
    """
    Scenario 3: Multi-Step Coordination

    Router decomposes the task into:
    - get premium customers
    - get high-priority tickets for their IDs
    - synthesize a status report
    """
    print("=== Scenario 3: Multi-Step Coordination ===")
    user_text = "What's the status of all high-priority tickets for premium customers?"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

async def main() -> None:
    # 5 required test cases
    await simple_query()
    await coordinated_query()
    await complex_query()
    await escalation_query()
    await multi_intent_query()

    # 3 orchestration scenarios
    await scenario_task_allocation()
    await scenario_negotiation_escalation()
    await scenario_multi_step_coordination()


if __name__ == "__main__":
    asyncio.run(main())
