# run_a2a_servers.py
import asyncio
import threading
import time

from adk_agents import (
    customer_data_agent,
    customer_data_agent_card,
    support_agent,
    support_agent_card,
    router_agent,
    router_agent_card,
)
from a2a_utils import run_agent_server


async def start_all_agents() -> None:
    tasks = [
        asyncio.create_task(run_agent_server(customer_data_agent, customer_data_agent_card, 9101)),
        asyncio.create_task(run_agent_server(support_agent, support_agent_card, 9102)),
        asyncio.create_task(run_agent_server(router_agent, router_agent_card, 9200)),
    ]

    await asyncio.sleep(2)
    print("All agents are running:")
    print("  - Customer Data Agent: http://127.0.0.1:9101")
    print("  - Support Agent:      http://127.0.0.1:9102")
    print("  - Router Agent:       http://127.0.0.1:9200")

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("Shutting down agents...")


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_all_agents())


if __name__ == "__main__":
    # Optional: run in foreground for debugging
    main()
