# mcp_server.py
import argparse
import json
import sys
from typing import Any, Dict, List, Optional

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:
    # Lightweight fallback so the module can import without the mcp package installed.
    class FastMCP:
        def __init__(self, name: str) -> None:
            self.name = name
            self._tools = {}

        def tool(self):
            def decorator(fn):
                self._tools[fn.__name__] = fn
                return fn

            return decorator

        def run(self) -> None:
            raise ImportError(
                "mcp package not installed; install requirements.txt to run the MCP server."
            )


from database_setup import bootstrap_database
import db
import db_tools


# -----------------------------------------------------------------------------
# Bootstrap database before serving any MCP requests
# -----------------------------------------------------------------------------
bootstrap_database(reset_existing=False)
server = FastMCP("customer-data-mcp")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _json_safe(value: Any) -> Any:
    """
    Ensure all values are JSON-serializable.

    - Decode bytes to UTF-8 strings.
    - Recursively handle lists and dicts.
    """
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value


def _wrap_result(result: Any) -> Any:
    """
    Apply _json_safe to the entire result object.
    """
    return _json_safe(result)


# -----------------------------------------------------------------------------
# MCP tools backed by db_tools (JSON-friendly envelopes)
# These are the tools the Router / Agents will actually use.
# -----------------------------------------------------------------------------


@server.tool()
def health_check() -> Dict[str, Any]:
    """
    Perform a simple health check to verify that the database is reachable.
    """
    return _wrap_result(db_tools.health_check())


@server.tool()
def get_customer(customer_id: int) -> Dict[str, Any]:
    """
    Fetch a single customer by ID.
    Returns:
        {
          "success": bool,
          "customer": { ... } | null,
          "error": str | optional
        }
    """
    return _wrap_result(db_tools.get_customer(customer_id))


@server.tool()
def list_customers(status: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    List customers, optionally filtered by status.
    Returns:
        {
          "success": bool,
          "customers": [ ... ],
          "error": str | optional
        }
    """
    return _wrap_result(db_tools.list_customers(status=status, limit=limit))


@server.tool()
def list_active_customers() -> Dict[str, Any]:
    """
    List all active customers.
    """
    return _wrap_result(db_tools.list_active_customers())


@server.tool()
def list_premium_customers() -> Dict[str, Any]:
    """
    List all premium customers.
    For this assignment, this corresponds to the synthetic premium record(s)
    created by database_setup.py (e.g. customer with ID 12345).
    """
    return _wrap_result(db_tools.list_premium_customers())


@server.tool()
def open_tickets_for_customer(customer_id: int) -> Dict[str, Any]:
    """
    Return all open tickets for a given customer.
    """
    return _wrap_result(db_tools.open_tickets_for_customer(customer_id))


@server.tool()
def high_priority_tickets_for_customers(customer_ids: List[int]) -> Dict[str, Any]:
    """
    Return all high-priority tickets for a list of customers.
    """
    return _wrap_result(db_tools.high_priority_tickets_for_customers(customer_ids))


@server.tool()
def billing_context_for_customer(customer_id: int) -> Dict[str, Any]:
    """
    Return billing-related ticket context for a given customer.
    This is used for escalation / billing scenarios.
    """
    return _wrap_result(db_tools.billing_context_for_customer(customer_id))


@server.tool()
def customer_ticket_history(customer_id: int) -> Dict[str, Any]:
    """
    Return the full ticket history for a customer.
    Used in the multi-intent test scenario.
    """
    return _wrap_result(db_tools.customer_ticket_history(customer_id))


@server.tool()
def update_customer_email(customer_id: int, new_email: str) -> Dict[str, Any]:
    """
    Update the email address of a customer and return the updated record.
    """
    return _wrap_result(db_tools.update_customer_email(customer_id, new_email))


# -----------------------------------------------------------------------------
# Legacy-style tools (dict/list of rows) kept for backwards compatibility.
# These are not strictly necessary for the assignment, but they do not hurt.
# -----------------------------------------------------------------------------


@server.tool()
def create_ticket(
    customer_id: int,
    issue: str,
    priority: str = "medium",
    status: str = "open",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new ticket for a customer.

    This tool directly uses db.create_ticket and returns a dict representing the row.
    """
    path = db.DB_PATH if db_path is None else db_path
    ticket = db.create_ticket(
        customer_id,
        issue,
        priority=priority,
        status=status,
        db_path=path,
    )
    return _wrap_result(ticket)


# -----------------------------------------------------------------------------
# Simple JSON-RPC 2.0 stdio server for environments without full MCP stack.
# This allows you to test tools quickly using plain stdin/stdout.
# -----------------------------------------------------------------------------


def _simple_stdio_server() -> None:
    """
    Lightweight JSON-RPC 2.0 stdio server.

    Only supports the registered tool methods and expects one request per line.
    Example request:
        {"jsonrpc": "2.0", "id": 1, "method": "get_customer", "params": {"customer_id": 5}}
    """
    tool_map = {
        "health_check": health_check,
        "get_customer": get_customer,
        "list_customers": list_customers,
        "list_active_customers": list_active_customers,
        "list_premium_customers": list_premium_customers,
        "open_tickets_for_customer": open_tickets_for_customer,
        "high_priority_tickets_for_customers": high_priority_tickets_for_customers,
        "billing_context_for_customer": billing_context_for_customer,
        "customer_ticket_history": customer_ticket_history,
        "update_customer_email": update_customer_email,
        "create_ticket": create_ticket,
    }

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            # Ignore malformed lines
            continue

        method = req.get("method")
        params = req.get("params", {}) or {}
        req_id = req.get("id")

        if method not in tool_map:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": "Method not found"},
            }
        else:
            try:
                result = tool_map[method](**params)
                resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
            except Exception as exc:  # pylint: disable=broad-except
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(exc)},
                }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


@server.tool()
def list_active_customers_with_open_tickets(
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return all active customers who currently have non-resolved tickets.

    This is a convenience tool for complex queries like:
    'Show me all active customers who have open tickets.'
    """
    path = db.DB_PATH if db_path is None else db_path
    rows = db.list_active_customers_with_open_tickets(db_path=path)
    return [{k: _json_safe(v) for k, v in row.items()} for row in rows]


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Customer data MCP server")
    parser.add_argument(
        "--simple-stdio",
        action="store_true",
        help="Run in simple JSON-RPC stdio mode",
    )
    args = parser.parse_args()

    if args.simple_stdio:
        _simple_stdio_server()
    else:
        server.run()
