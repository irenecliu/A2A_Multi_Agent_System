# Multi-Agent Customer Service System

**(Agent-to-Agent Coordination + MCP-Backed Data Layer)**

This project implements a practical **multi-agent customer service system** using **Agent-to-Agent (A2A) coordination** and an **MCP-backed customer data service**. The system is composed of three specialized agents:

* **Router Agent (Orchestrator)** – receives all user queries, analyzes intent, and coordinates multi-step workflows.
* **Customer Data Agent (Specialist)** – accesses the SQLite customer database exclusively via MCP-style tools.
* **Support Agent (Specialist)** – generates user-facing responses, handles escalation, and summarizes results.

Together, these agents demonstrate realistic customer-service workflows including **task allocation, negotiation, escalation, and multi-step coordination**.

---

## Environment Setup

### Install Dependencies

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

Alternatively:

```bash
pip install -r requirements.txt
```

---

## Quick Start

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize the database with demo data
python database_setup.py

# 4. Start the MCP server (data layer)
python mcp_server.py

# 5. Start the A2A agents
python run_a2a_servers.py

# 6. Run the end-to-end scenario tests
python run_demo.py
```

---

## Project Structure

```text
.
├── database_setup.py          # Seeds the SQLite database with demo customer & ticket data
├── db.py                      # Shared low-level SQLite helpers
├── db_tools.py                # High-level MCP-style data access tools
├── mcp_server.py              # FastMCP server exposing database tools
├── mcp_client.py              # Lightweight JSON-RPC client for MCP
├── adk_agents.py              # Defines Customer Data Agent, Support Agent, and Router Agent
├── run_a2a_servers.py         # Starts all A2A HTTP servers
├── run_demo.py                # Runs all required assignment scenarios
├── scenario1_task_allocation.py
├── scenario2_negotiation_escalation.py
├── scenario3_multi_step_coordination.py
└── requirements.txt
```

---

## System Architecture

**High-Level Flow**

```text
User
 ↓
Router Agent (Orchestrator)
 ↓
Customer Data Agent (via MCP tools)
 ↓
Support Agent (final response)
```

**Key Design Principles**

* The **Customer Data Agent never writes directly to the database**. All DB access is done via MCP-backed tools.
* The **Router Agent performs orchestration only**, never directly performing data access.
* The **Support Agent produces all user-facing responses** based strictly on structured JSON returned by the Customer Data Agent.
* All escalation flows create **high-priority tickets** in the database.

---

## Assignment Scenarios Covered

This project fully implements all required assignment scenarios:

### 1. Task Allocation

**Query:**

> *"I'm customer 12345 and need help upgrading my account."*

**Flow:**
Router → Customer Data Agent → Support Agent

---

### 2. Negotiation / Escalation

**Query:**

> *"I want to cancel my subscription but I'm having billing issues."*

**Flow:**

* Router detects multiple intents
* Customer Data Agent retrieves billing context
* Support Agent escalates and confirms ticket creation

---

### 3. Multi-Step Coordination

**Query:**

> *"What's the status of all high-priority tickets for premium customers?"*

**Flow:**

* Retrieve premium customers
* Retrieve their high-priority open tickets
* Aggregate and summarize results

---

### 4. Additional Functional Tests

* Simple lookup:

  > *"Get customer information for ID 5"*

* Active customers with open tickets

* Parallel update + history retrieval (multi-intent)

* Direct billing escalation with automatic ticket creation

---

## Notebook Execution Option (Colab)

This project can also be executed end-to-end using Jupyter Notebook or Google Colab:

* Upload all source files to Colab
* Upload the SQLite database
* Run `database_setup.py`
* Start MCP and A2A services inside the notebook
* Execute the scenario test cells

Alternatively, the GitHub repository can be cloned directly in Colab and executed.

---

## Known Runtime Consideration (LLM Quota)

Some complex scenarios (especially multi-step premium ticket reports) rely on **Gemini 2.5 Pro**. Under limited API quota, responses may occasionally return fallback messages such as *resource exhausted*.

This does **not** indicate a system design failure. The full logic is implemented in:

```python
db_tools.list_active_customers_with_open_tickets()
db_tools.high_priority_tickets_for_customers()
```

These functions can always be verified independently at the database level.

---

## Conclusion

This project delivers a complete hands-on implementation of a **realistic multi-agent customer service system** using both **Agent-to-Agent (A2A) orchestration** and an **MCP-backed data layer**. By cleanly separating responsibilities across:

* a **Router Agent** (orchestration),
* a **Customer Data Agent** (database & validation),
* and a **Support Agent** (user-facing communication and escalation),

the system successfully models **task allocation, intent negotiation, escalation handling, and multi-step coordination**.

One of the core challenges was deciding **how much workflow logic to explicitly structure inside the agents** in order to reliably satisfy all assignment constraints. Supporting upgrades, billing disputes, ticket reporting, and multi-intent requests required designing a rich and explicit intent space across all agents. This process closely mirrors real-world multi-agent system design, where scalability depends not on a single LLM call, but on **clear intent modeling, strict agent boundaries, and predictable orchestration patterns**.

Overall, this project provided a valuable, system-level perspective on how production-grade multi-agent architectures are designed, debugged, and validated.