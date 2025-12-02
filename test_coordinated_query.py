import asyncio

from a2a_utils import CustomerServiceA2AClient

ROUTER_URL = "http://localhost:9200"
client = CustomerServiceA2AClient()


async def coordinated_query() -> None:
    """Coordinated Query: data fetch + support response."""
    print("=== Coordinated Query ===")
    user_text = "I'm customer 1 and need help upgrading my account"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def main() -> None:
    await coordinated_query()


if __name__ == "__main__":
    asyncio.run(main())
