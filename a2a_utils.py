# a2a_utils.py
"""
Utilities for running ADK agents over A2A and calling them from Python.
"""

from dotenv import load_dotenv
load_dotenv()

from typing import Any, Dict

import httpx
import nest_asyncio
import uvicorn
import sniffio

from a2a.client import ClientConfig, ClientFactory, create_text_message_object
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, TransportProtocol
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a.executor.a2a_agent_executor import (
    A2aAgentExecutor,
    A2aAgentExecutorConfig,
)
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# ---- Patch sniffio for Python 3.14 / httpx compatibility ----
# Some versions of httpx/httpcore + sniffio cannot detect the async
# environment on Python 3.14 yet, which raises AsyncLibraryNotFoundError.
# Here we force sniffio to report "asyncio" as the current library when
# detection fails, which is exactly what we are using.
try:
    sniffio.current_async_library()
except sniffio.AsyncLibraryNotFoundError:  # type: ignore[attr-defined]
    def _force_asyncio() -> str:
        return "asyncio"
    sniffio.current_async_library = _force_asyncio  # type: ignore[assignment]

nest_asyncio.apply()


# ---------- Server-side helpers ----------


def build_a2a_app(agent, agent_card) -> A2AStarletteApplication:
    """Create an A2A HTTP application for a given ADK agent."""
    runner = Runner(
        app_name=agent.name,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )

    executor = A2aAgentExecutor(runner=runner, config=A2aAgentExecutorConfig())
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )

    return A2AStarletteApplication(agent_card=agent_card, http_handler=handler)


async def run_agent_server(agent, agent_card, port: int) -> None:
    """Run a single ADK agent as an A2A HTTP server on the given port."""
    app = build_a2a_app(agent, agent_card)
    config = uvicorn.Config(
        app.build(),
        host="127.0.0.1",
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


# ---------- Client-side helper (used by run_demo) ----------


class CustomerServiceA2AClient:
    """
    Lightweight A2A client to send text messages to an agent URL.

    The implementation follows the official A2A SDK pattern, but is scoped
    to this customer-service assignment.
    """

    def __init__(self, default_timeout: float = 240.0) -> None:
        # Cache of agent card JSON per agent_url
        self._agent_info_cache: Dict[str, Dict[str, Any] | None] = {}
        self.default_timeout = default_timeout

    async def send_text(self, agent_url: str, message: str) -> str:
        """Send a single text message to an agent and return the text reply."""
        timeout_config = httpx.Timeout(
            timeout=self.default_timeout,
            connect=10.0,
            read=self.default_timeout,
            write=10.0,
            pool=5.0,
        )

        async with httpx.AsyncClient(timeout=timeout_config) as httpx_client:
            # 1) Get agent card JSON (use cache if possible)
            if (
                agent_url in self._agent_info_cache
                and self._agent_info_cache[agent_url] is not None
            ):
                agent_card_data = self._agent_info_cache[agent_url]
            else:
                resp = await httpx_client.get(
                    f"{agent_url}{AGENT_CARD_WELL_KNOWN_PATH}"
                )
                resp.raise_for_status()
                agent_card_data = resp.json()
                self._agent_info_cache[agent_url] = agent_card_data

            # 2) Build AgentCard object
            agent_card = AgentCard(**agent_card_data)

            # 3) Build A2A client using the official pattern
            config = ClientConfig(
                httpx_client=httpx_client,
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                use_client_preference=True,
            )
            factory = ClientFactory(config)
            client = factory.create(agent_card)

            # 4) Wrap the message into A2A content and send
            message_obj = create_text_message_object(content=message)

            responses = []
            async for response in client.send_message(message_obj):
                responses.append(response)

            # 5) Extract text from the first Task in the first response tuple
            if (
                responses
                and isinstance(responses[0], tuple)
                and len(responses[0]) > 0
            ):
                task = responses[0][0]
                try:
                    return task.artifacts[0].parts[0].root.text
                except (AttributeError, IndexError, TypeError):
                    return str(task)

            return "No response received"
