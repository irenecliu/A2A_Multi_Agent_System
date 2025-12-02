import asyncio

from a2a_utils import CustomerServiceA2AClient

ROUTER_URL = "http://localhost:9200"
client = CustomerServiceA2AClient()


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


async def main() -> None:
    await scenario_multi_step_coordination()


if __name__ == "__main__":
    asyncio.run(main())
