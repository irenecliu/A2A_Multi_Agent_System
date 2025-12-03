# Multi-Agent Customer Service (A2A + MCP)

This project implements the Assignment 5 multi-agent customer-service system.

## 1. Repository Layout

```text
multi-agent-customer-service/
├── agents/                     # Agent configuration / helper modules (if any)
├── data/                       # SQLite DB lives here after setup
├── logs/                       # Runtime logs from servers & scenarios
├── a2a_client_scenarios.py     # HTTP client hitting A2A servers (end-to-end)
├── a2a_utils.py                # Shared A2A helper functions (HTTP calls, formatting, etc.)
├── adk_agents.py               # ADK A2A agent definitions & server startup helpers
├── database_setup.py           # Build & seed the SQLite database
├── db.py                       # Core DB helper functions (connect, queries, etc.)
├── db_tools.py                 # Thin wrappers exposing DB operations as MCP tools
├── end-to-end-output.txt       # The full output from `run_demo.py`
├── mcp_client.py               # Simple client for testing MCP directly (tool calls)
├── mcp_server.py               # FastMCP server exposing DB tools over HTTP
├── run_a2a_servers.py          # Starts Router + Customer Data + Support A2A servers
├── run_demo.py                 # Main entry point – runs all required scenarios (3 scenarios and 5 test queries)
├── scenario1_task_allocation.py        # Scenario script: basic task allocation
├── scenario2_negotiation_escalation.py # Scenario script: negotiation & escalation
├── scenario3_multi_step_coordination.py# Scenario script: multi-step workflows
├── test_simple_query.py        # Required test: simple customer lookup
├── test_coordinated_query.py   # Required test: router + data+support coordination
├── test_complex_query.py       # Required test: multi-step complex query
├── test_escalation_query.py    # Required test: escalation scenario
├── test_multi_intent_query.py  # Required test: multi-intent handling
├── requirements.txt            # Python dependencies
└── README.md                   # (this file)
```

### File Introduction

* **`database_setup.py`**
  Creates `data/customer_service.db` and seeds customers & tickets.

* **`db.py`**
  Low-level DB helpers: open connection, run SELECT/UPDATE queries.

* **`db_tools.py`**
  Wraps DB functions into MCP tool definitions (e.g. `get_customer`, `get_open_tickets`).

* **`mcp_server.py`**
  FastMCP server that:

  * Registers tools from `db_tools.py`
  * Serves them over HTTP for remote agents / clients

* **`adk_agents.py`**
  Defines:

  * **Customer Data Agent** (calls MCP tools to query the DB)
  * **Support Agent** (formats responses, handles escalation phrasing)
  * **Router Agent** (decides which agent to call, combines results)
    And provides functions used by `run_a2a_servers.py` to start A2A services.

* **`run_a2a_servers.py`**
  Bootstraps the A2A services, usually:

  * Starts a **Customer Data Agent** HTTP endpoint
  * Starts a **Support Agent** HTTP endpoint
  * Starts a **Router Agent** that talks to the other two

* **`a2a_utils.py`**
  Shared utilities for:

  * Building HTTP requests to A2A endpoints
  * Logging / pretty printing
  * Small helper functions reused across scenario scripts & tests

* **`a2a_client_scenarios.py`**
  A pure-client script that:

  * Sends example user queries to the Router Agent HTTP endpoint
  * Shows how the router calls the other agents and returns final answers

* **Scenario & test scripts (`scenario*.py`, `test_*.py`, `run_demo.py`)**
  Orchestrate complete end-to-end workflows to:

  * Reproduce the Assignment 5 required scenarios
  * Provide clean CLI entry points for SIMON5 tests

---

## 2. Prerequisites

* **Python**: 3.11 (recommended; 3.10+ may work but is not tested)
* **pip**: recent version
* **git**: to clone the repository

The commands below assume macOS / Linux. On Windows, replace `python3` with `python` and `source venv/bin/activate` with `venv\Scripts\activate`.

---

## 3. Getting Started

### 3.1 Clone the repository

```bash
git clone <YOUR-REPO-URL>.git
cd multi-agent-customer-service
```

> Replace `<YOUR-REPO-URL>` with the URL of your GitHub repo.

### 3.2 Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

You should now see `(venv)` in your shell prompt.

### 3.3 Install dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

If for any reason A2A / ADK dependencies are not present in `requirements.txt`, you can explicitly install them with:

```bash
pip install -U \
  google-adk==1.19.0 \
  "a2a-sdk[http-server]" \
  nest-asyncio \
  sniffio \
  anyio \
  httpx \
  uvicorn \
  starlette \
  fastapi \
  python-dotenv \
  requests
```

---

## 4. Initialize the Database

Before running any agents, create and seed the SQLite database:

```bash
python database_setup.py
```

This will:

* Create `data/customer_service.db` (if it does not exist)
* Insert demo customers and tickets used in all scenarios

You should see a message similar to:

```text
Database initialized with N customers and N tickets at data/customer_service.db
```

---

## 5. Run the MCP Server

The MCP server exposes the customer-service database as tools (e.g. `get_customer`, `get_open_tickets`) that remote agents can call.

In Terminal 1, with the virtual environment activated:

```bash
python mcp_server.py
```

The server will:

* Import tool definitions from `db_tools.py`
* Start a FastMCP HTTP server
* Log the host/port it is listening on (see constants / settings inside `mcp_server.py`)

Leave this terminal running.

---

## 6. Run the A2A Agent Servers

The A2A servers host the Router Agent, Customer Data Agent, and Support Agent as HTTP services that the client/tests will call.

In Terminal 2, again with the virtual environment activated and from the project root:

```bash
source venv/bin/activate
python run_a2a_servers.py
```

This script will:

1. Start the Customer Data Agent (configured to call the MCP server tools).
2. Start the Support Agent (handles response formatting, escalation language, etc.).
3. Start the Router Agent (receives user queries and decides which agent(s) to call).

All ports / base URLs are configured inside `adk_agents.py` and/or `run_a2a_servers.py`.
The log output will show each agent’s HTTP endpoint details.

Leave this terminal running as well.

---

## 7. Run the End-to-End Demo ( Entry Point)

With both the MCP server and A2A servers running:

In Terminal 3:

```bash
source venv/bin/activate
python run_demo.py
```

This script:

* Calls the Router Agent over HTTP
* Runs all required scenarios:
---

## 8. Running Individual Scenario Scripts

You can also run the scenario scripts individually for debugging.

Assuming MCP + A2A servers are running:

```bash
python scenario1_task_allocation.py
python scenario2_negotiation_escalation.py
python scenario3_multi_step_coordination.py
```

These scripts send specific prompts to the Router Agent and print the responses.

The **A2A HTTP client** is factored out into:

```bash
python a2a_client_scenarios.py
```

which demonstrates how to:

* Build HTTP requests to the Router Agent
* Trace how the router delegates work to Customer Data & Support agents
* Aggregate and display final responses

---

## 9. Running the Test Scripts

For finer-grained tests (aligned with SIMON5 requirements), run:

```bash
python test_simple_query.py
python test_coordinated_query.py
python test_complex_query.py
python test_escalation_query.py
python test_multi_intent_query.py   # if required / for extended testing
```

Each script:

* Sends a predefined user query (or queries) to the Router Agent
* Verifies that the returned response matches the expected behavior
* Prints the result to stdout and may write log files into `logs/`

> **Note:** MCP + A2A servers must be running for these tests to succeed.

---

## 10. Conlusion

This project helped me understand how a real multi-agent system is structured and coordinated using MCP and A2A, especially the importance of separating responsibilities between the Router, Data, and Support agents. I learned how tool-based communication enables agents to interact with databases in a reliable and scalable way, and how end-to-end agent workflows are built over HTTP services.

The main challenges came from debugging inter-agent communication, managing multiple running servers, and aligning tool interfaces with agent expectations. Small configuration issues such as ports, URLs, or environment variables often caused hard-to-trace errors, but resolving them greatly improved my system-level debugging skills. I've first install MCP Server correctly but didnt implement the agents (I think it's because of I didn't call MCP, instead, I was just retrieving data from the SQLite database). And that's the most challenging part for me.