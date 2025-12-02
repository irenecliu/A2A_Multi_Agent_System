import asyncio

from a2a_utils import CustomerServiceA2AClient

ROUTER_URL = "http://localhost:9200"
client = CustomerServiceA2AClient()


async def scenario_task_allocation() -> None:
    """
    Scenario 1: Task Allocation

    Router receives the query, fetches customer context, and routes
    handling to the appropriate specialist path.
    """
    print("=== Scenario 1: Task Allocation ===")
    user_text = "I need help with my account, customer ID 12345"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def main() -> None:
    await scenario_task_allocation()


if __name__ == "__main__":
    asyncio.run(main())
