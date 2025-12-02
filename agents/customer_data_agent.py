from typing import Dict, List, Optional

from agents.base import Agent, AgentMessage
from mcp_client import MCPDataClient


class CustomerDataAgent(Agent):
    """
    Specialist agent that wraps MCP data access tools via JSON-RPC to the MCP server process.
    """

    def __init__(self, logger, db_path: Optional[str] = None, client: Optional[MCPDataClient] = None) -> None:
        super().__init__("customer-data-agent", logger)
        self.db_path = db_path
        self.client = client or MCPDataClient()
        self._owns_client = client is None

    def handle(self, message: AgentMessage) -> AgentMessage:
        intent = message.intent or "info"
        payload = message.payload or {}
        response_payload: Dict = {}
        content: str

        if intent == "get_customer":
            customer_id = int(payload["customer_id"])
            customer = self._call_tool("get_customer", {"customer_id": customer_id, "db_path": self.db_path})
            response_payload["customer"] = customer
            content = f"Customer {customer_id} fetched"
        elif intent == "list_customers":
            customers = self._call_tool(
                "list_customers",
                {"status": payload.get("status"), "limit": payload.get("limit", 10), "db_path": self.db_path},
            )
            response_payload["customers"] = customers
            content = f"Listed {len(customers)} customers"
        elif intent == "update_customer":
            updated = self._call_tool(
                "update_customer",
                {"customer_id": payload["customer_id"], "data": payload.get("data", {}), "db_path": self.db_path},
            )
            response_payload["customer"] = updated
            content = f"Customer {payload['customer_id']} updated"
        elif intent == "create_ticket":
            ticket = self._call_tool(
                "create_ticket",
                {
                    "customer_id": payload["customer_id"],
                    "issue": payload["issue"],
                    "priority": payload.get("priority", "medium"),
                    "status": payload.get("status", "open"),
                    "db_path": self.db_path,
                },
            )
            response_payload["ticket"] = ticket
            content = f"Ticket created for customer {payload['customer_id']}"
        elif intent == "get_history":
            history = self._call_tool(
                "get_customer_history",
                {"customer_id": payload["customer_id"], "db_path": self.db_path},
            )
            response_payload["history"] = history
            content = f"Fetched history for customer {payload['customer_id']}"
        else:
            content = f"Unknown intent: {intent}"

        reply = AgentMessage(
            sender=self.name,
            recipient=message.sender,
            content=content,
            intent=intent,
            payload=response_payload,
        )
        self.logger.record(reply)
        return reply

    @staticmethod
    def _normalize_result(raw):
        """
        MCP client compatibility: unwrap CallToolResult or dict-like envelopes to the underlying payload.
        """
        # mcp.client may return CallToolResult objects
        if hasattr(raw, "result"):
            raw = raw.result
        # Some clients wrap as {"result": ...}
        if isinstance(raw, dict) and "result" in raw and len(raw) == 1:
            raw = raw["result"]
        return raw

    def get_open_tickets_for_active_customers(self, priority: Optional[str] = None) -> List[dict]:
        """
        Helper used in multi-step coordination. Uses only MCP-exposed tools.
        """
        customers = self._call_tool("list_customers", {"status": "active", "limit": 100, "db_path": self.db_path})
        tickets: List[dict] = []
        for customer in customers:
            history = self._call_tool(
                "get_customer_history",
                {"customer_id": customer["id"], "db_path": self.db_path},
            )
            for ticket in history:
                if ticket["status"] != "resolved":
                    tickets.append(ticket)

        if priority:
            tickets = [t for t in tickets if t.get("priority") == priority]
        # De-duplicate tickets in case of overlaps
        seen = set()
        unique: List[dict] = []
        for t in tickets:
            if t["id"] in seen:
                continue
            seen.add(t["id"])
            unique.append(t)
        return unique

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def _call_tool(self, name: str, args: Dict) -> Dict:
        """
        Call an MCP tool and log the request/response as agent-to-agent messages.
        """
        request = AgentMessage(sender=self.name, recipient="mcp-server", content=f"Call {name}", intent=name, payload=args)
        self.logger.record(request)
        raw = getattr(self.client, name)(**args)
        result = self._normalize_result(raw)
        response = AgentMessage(
            sender="mcp-server",
            recipient=self.name,
            content=f"{name} completed",
            intent=name,
            payload={"result": result},
        )
        self.logger.record(response)
        return result
