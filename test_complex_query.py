import asyncio

from a2a_utils import CustomerServiceA2AClient

ROUTER_URL = "http://localhost:9200"
client = CustomerServiceA2AClient()


async def complex_query() -> None:
    """Complex Query: active customers with open tickets."""
    print("=== Complex Query ===")
    user_text = "Show me all active customers who have open tickets"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def main() -> None:
    await complex_query()


if __name__ == "__main__":
    asyncio.run(main())
