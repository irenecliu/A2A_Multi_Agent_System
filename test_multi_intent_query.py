import asyncio

from a2a_utils import CustomerServiceA2AClient

ROUTER_URL = "http://localhost:9200"
client = CustomerServiceA2AClient()


async def multi_intent_query() -> None:
    """Multi-Intent: update profile + show history in one request."""
    print("=== Multi-Intent ===")
    user_text = "My customer ID is 4. Update my email to new@email.com and show my ticket history"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def main() -> None:
    await multi_intent_query()


if __name__ == "__main__":
    asyncio.run(main())
