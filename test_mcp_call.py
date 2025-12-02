from mcp_client import MCPDataClient

if __name__ == "__main__":
    with MCPDataClient() as client:
        result = client.get_customer(5, None)
        print("MCP result:", result)
