import asyncio

from a2a_utils import CustomerServiceA2AClient

ROUTER_URL = "http://localhost:9200"
client = CustomerServiceA2AClient()


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


async def main() -> None:
    await scenario_negotiation_escalation()


if __name__ == "__main__":
    asyncio.run(main())
