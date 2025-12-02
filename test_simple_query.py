import asyncio

from a2a_utils import CustomerServiceA2AClient

ROUTER_URL = "http://localhost:9200"
client = CustomerServiceA2AClient()


async def simple_query() -> None:
    """Simple Query: single-agent, straightforward MCP call."""
    print("=== Simple Query ===")
    user_text = "Get customer information for ID 5"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def main() -> None:
    await simple_query()


if __name__ == "__main__":
    asyncio.run(main())
