"""
MCP stdio client used by CustomerDataAgent to reach the MCP server process.

This client speaks a minimal JSON-RPC 2.0 protocol over stdio to the server started
via `python mcp_server.py --simple-stdio`. It does not import or call the database
helpers directly, ensuring the agent topology stays User -> Router -> Data Agent -> MCP.
"""
import json
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Optional

SERVER_CMD = ["python3", "mcp_server.py", "--simple-stdio"]


class MCPProcessClient:
    def __init__(self, workdir: Optional[Path] = None) -> None:
        self.workdir = workdir or Path(__file__).resolve().parent
        self.proc = subprocess.Popen(
            SERVER_CMD,
            cwd=self.workdir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._id = 0
        self._lock = threading.Lock()

    def call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """
        Send a JSON-RPC request and wait for the corresponding response.
        """
        if not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError("MCP server process is not available.")

        with self._lock:
            self._id += 1
            req_id = self._id

        request = {"jsonrpc": "2.0", "id": req_id, "method": name, "params": args}
        self.proc.stdin.write(json.dumps(request) + "\n")
        self.proc.stdin.flush()

        # Read lines until we find the matching id
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server terminated unexpectedly.")
            try:
                resp = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            if resp.get("id") != req_id:
                continue
            if "error" in resp:
                raise RuntimeError(resp["error"].get("message", "Unknown MCP error"))
            return resp.get("result")

    def close(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None


class MCPDataClient:
    """
    Thin wrapper around MCPProcessClient exposing typed methods for agents.
    """

    def __init__(self, process_client: Optional[MCPProcessClient] = None) -> None:
        self._owns_process = process_client is None
        self.client = process_client or MCPProcessClient()

    def get_customer(self, customer_id: int, db_path: Optional[str] = None) -> Any:
        return self.client.call_tool("get_customer", {"customer_id": customer_id, "db_path": db_path})

    def list_customers(self, status: Optional[str], limit: int, db_path: Optional[str]) -> Any:
        return self.client.call_tool("list_customers", {"status": status, "limit": limit, "db_path": db_path})

    def update_customer(self, customer_id: int, data: Dict[str, Any], db_path: Optional[str]) -> Any:
        return self.client.call_tool("update_customer", {"customer_id": customer_id, "data": data, "db_path": db_path})

    def create_ticket(
        self, customer_id: int, issue: str, priority: str, status: str, db_path: Optional[str]
    ) -> Any:
        return self.client.call_tool(
            "create_ticket",
            {"customer_id": customer_id, "issue": issue, "priority": priority, "status": status, "db_path": db_path},
        )

    def get_customer_history(self, customer_id: int, db_path: Optional[str]) -> Any:
        return self.client.call_tool("get_customer_history", {"customer_id": customer_id, "db_path": db_path})

    def close(self) -> None:
        if self._owns_process:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
