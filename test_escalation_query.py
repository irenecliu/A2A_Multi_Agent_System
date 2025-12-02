import asyncio

from a2a_utils import CustomerServiceA2AClient

ROUTER_URL = "http://localhost:9200"
client = CustomerServiceA2AClient()


async def escalation_query() -> None:
    """Escalation: urgent billing issue."""
    print("=== Escalation ===")
    user_text = "I've been charged twice, please refund immediately!"
    print(f"User: {user_text}")
    answer = await client.send_text(ROUTER_URL, user_text)
    print(f"Assistant: {answer}\n")


async def main() -> None:
    await escalation_query()


if __name__ == "__main__":
    asyncio.run(main())
