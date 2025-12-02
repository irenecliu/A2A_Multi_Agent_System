# a2a_client_scenarios.py
import asyncio
from typing import Any, Dict, List

import httpx
from a2a.client import ClientConfig, ClientFactory, create_text_message_object


class SimpleA2AClient:
    """Minimal A2A client for calling an agent over HTTP."""

    def __init__(self, timeout: float = 120.0):
        self._cache: Dict[str, Dict[str, Any] | None] = {}
        self.timeout = timeout

    async def send_text(self, agent_url: str, message: str) -> str:
        timeout_cfg = httpx.Timeout(
            timeout=self.timeout,
            connect=10.0,
            read=self.timeout,
            write=10.0,
            pool=5.0,
        )

        async with httpx.AsyncClient(timeout=timeout_cfg) as session:
            # Discover or re-use agent card
            if agent_url not in self._cache:
                config = ClientConfig()
                factory = ClientFactory(config=config, http_client=session)
                client = await factory.create_client_for_url(agent_url)
                self._cache[agent_url] = {"client": client}
            client = self._cache[agent_url]["client"]

            task = await client.create_task(
                create_text_message_object(message),
                response_mode="blocking",
            )

            # Extract the final text from the task result
            if task.result and getattr(task.result, "output", None):
                output = task.result.output
                parts: List[Any] = getattr(output, "parts", [])
                if parts:
                    root = getattr(parts[0], "root", None)
                    text = getattr(root, "text", None)
                    if text:
                        return text

            # Fallback: dump something readable
            return f"Task finished but no text output. Raw task: {task!r}"


a2a_client = SimpleA2AClient()


async def scenario_simple_query() -> None:
    print("=== Simple Query ===")
    response = await a2a_client.send_text(
        "http://localhost:9200",
        "Get customer information for ID 5",
    )
    print(response)


async def scenario_coordinated() -> None:
    print("\n=== Coordinated Query ===")
    response = await a2a_client.send_text(
        "http://localhost:9200",
        "I'm customer 12345 and need help upgrading my account.",
    )
    print(response)


async def scenario_complex() -> None:
    print("\n=== Complex Query ===")
    response = await a2a_client.send_text(
        "http://localhost:9200",
        "Show me all active customers who have open tickets.",
    )
    print(response)


async def scenario_escalation() -> None:
    print("\n=== Escalation ===")
    response = await a2a_client.send_text(
        "http://localhost:9200",
        "I've been charged twice, please refund immediately!",
    )
    print(response)


async def scenario_multi_intent() -> None:
    print("\n=== Multi-Intent ===")
    response = await a2a_client.send_text(
        "http://localhost:9200",
        (
            "Update my email to [email protected] and show me the status of "
            "all my high-priority open tickets."
        ),
    )
    print(response)


async def main() -> None:
    await scenario_simple_query()
    await scenario_coordinated()
    await scenario_complex()
    await scenario_escalation()
    await scenario_multi_intent()


if __name__ == "__main__":
    asyncio.run(main())
