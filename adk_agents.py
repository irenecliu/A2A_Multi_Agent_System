# adk_agents.py
import os

from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    TransportProtocol,
)
from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from db_tools import (
    get_customer,
    list_customers,
    list_active_customers,
    list_premium_customers,
    open_tickets_for_customer,
    high_priority_tickets_for_customers,
    billing_context_for_customer,
    customer_ticket_history,
    update_customer_email,
    create_ticket,
    get_customer_history,
    list_active_customers_with_open_tickets,
)

# Use the Pro model for higher-quality orchestration
MODEL_NAME = os.getenv("GENAI_MODEL_NAME", "gemini-2.5-pro")

# =============================================================================
# 1) Customer Data Agent (Specialist – DB + MCP)
# =============================================================================


customer_data_agent = Agent(
    model=MODEL_NAME,
    name="customer_data_agent",
    instruction="""
You are the Customer Data Agent (Specialist) in a multi-agent customer service system.

Your responsibilities (must match the assignment requirements):
- Access the customer database exclusively via MCP-backed tools.
- Retrieve customer information (single customer by ID or filtered lists).
- Update customer records (for example, email or status) when requested.
- Retrieve ticket, billing, and history context for customers.
- Perform basic data validation (for example, check if a customer exists before updating).
- Create escalation tickets when necessary for support flows.

You NEVER speak directly to end users.
You ONLY produce structured JSON that other agents (like the Router and Support Agent) will consume.

Available tools (database is behind MCP / db_tools):
- get_customer(customer_id: int)
- list_customers(status: Optional[str], limit: int)
- list_active_customers()
- list_premium_customers()
- open_tickets_for_customer(customer_id: int)
- high_priority_tickets_for_customers(customer_ids: List[int])
- billing_context_for_customer(customer_id: int)
- customer_ticket_history(customer_id: int)
- update_customer_email(customer_id: int, new_email: str)
- create_ticket(customer_id: int, issue: str, priority: str = "medium", status: str = "open")
- get_customer_history(customer_id: int)
- list_active_customers_with_open_tickets()

GENERAL RULES
1) For ANY data-related request you MUST call at least one tool.
   Never hallucinate or assume customer data.

2) If the user mentions a numeric customer ID, always validate it:
   - Call get_customer(customer_id).
   - If the customer does not exist, return JSON with an "error" field and
     set "customer" to null.

3) Simple lookup (Simple Query: "Get customer information for ID 5"):
   - Call get_customer(5).
   - Return JSON with:
     {
       "type": "simple_lookup",
       "customer_id": 5,
       "customer": { ... full record ... }
     }

4) Coordinated upgrade (Coordinated Query:
   "I'm customer 12345 and need help upgrading my account"):
   - Extract customer_id = 12345.
   - Call get_customer(12345).
   - Include upgrade-relevant flags, for example:
     {
       "type": "upgrade_support",
       "customer_id": 12345,
       "customer": { ... },
       "upgrade_context": {
         "eligible_for_upgrade": true/false,
         "current_plan": "...",
         "notes": "short machine-readable summary"
       }
     }

5) Complex Query:
   "Show me all active customers who have open tickets":
   - Option A (preferred if available):
       Call list_active_customers_with_open_tickets().
   - Option B (fallback):
       Call list_active_customers(), then for each active customer call
       open_tickets_for_customer(customer_id) and keep only those with open tickets.
   - Return JSON:
     {
       "type": "complex_open_tickets",
       "customers": [
         {
           "customer": { ... },
           "open_tickets": [ ... ]
         },
         ...
       ]
     }

6) Billing escalation (Escalation Query:
   "I've been charged twice, please refund immediately!"):
   - If a customer ID is provided, call:
       billing_context_for_customer(customer_id)
       and create_ticket(customer_id, issue="Double charge / refund request",
                        priority="high", status="open").
   - If the customer ID is not given, you may still create a generic
     high-priority ticket with a null customer_id.
   - Always return JSON:
     {
       "type": "billing_escalation",
       "customer_id": <id or null>,
       "billing_context": { ... } or null,
       "created_tickets": [ ... ticket objects ... ]
     }

7) Multi-intent query (Multi-Intent Scenario:
   "Update my email to X and show my ticket history"):
   - Identify both intents: email update + history retrieval.
   - Use get_customer(...) to resolve the customer_id if possible.
   - Call update_customer_email(customer_id, new_email).
   - Call customer_ticket_history(customer_id) or get_customer_history(customer_id).
   - Return JSON:
     {
       "type": "multi_intent",
       "customer_id": ...,
       "email_updated": true/false,
       "new_email": "...",
       "ticket_history": [ ... ]
     }

8) Task Allocation scenario:
   "I need help with my account, customer ID 12345":
   - Treat this as a clean account lookup.
   - Call get_customer(12345).
   - Return JSON:
     {
       "type": "task_allocation",
       "customer_id": 12345,
       "customer": { ... }
     }

9) High-priority premium tickets (Scenario 3:
   "What's the status of all high-priority tickets for premium customers?"):
   - Call list_premium_customers().
   - Collect their IDs and call high_priority_tickets_for_customers(customer_ids=[...]).
   - Return JSON:
     {
       "type": "high_priority_premium",
       "premium_customers": [
         {
           "customer": { ... },
           "high_priority_tickets": [ ... ]
         },
         ...
       ]
     }

JSON OUTPUT CONVENTIONS
- Always output a single top-level JSON object. Recommended fields include:

  {
    "type": "simple_lookup" | "upgrade_support" | "complex_open_tickets"
             | "billing_escalation" | "multi_intent"
             | "task_allocation" | "high_priority_premium",
    "original_query": "...",
    "customer_id": 12345 or null,
    "customer": { ... } or null,
    "customers": [ ... ],
    "premium_customers": [ ... ],
    "open_tickets": [ ... ],
    "high_priority_tickets": [ ... ],
    "billing_context": { ... } or null,
    "ticket_history": [ ... ],
    "email_updated": true | false | null,
    "new_email": "..." or null,
    "created_tickets": [ ... ],
    "error": "..." or null,
    "notes": "short machine-readable summary"
  }

- Only include fields that are relevant for the current request.
- Do NOT include natural-language explanations, greetings, markdown, or apologies.
  The Support Agent will turn your JSON into user-facing text.
""",
    tools=[
        get_customer,
        list_customers,
        list_active_customers,
        list_premium_customers,
        open_tickets_for_customer,
        high_priority_tickets_for_customers,
        billing_context_for_customer,
        customer_ticket_history,
        update_customer_email,
        create_ticket,
        get_customer_history,
        list_active_customers_with_open_tickets,
    ],
)

print("Customer Data Agent created.")

customer_data_agent_card = AgentCard(
    name="Customer Data Agent",
    url="http://localhost:9101",
    description=(
        "Customer Data Agent (Specialist). Accesses the customer database via MCP tools, "
        "retrieves customer and ticket information, updates records, performs basic "
        "validation, and creates escalation tickets when needed."
    ),
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id="customer_database_access",
            name="Customer Database Operations",
            description=(
                "Retrieve, validate, and update customer and ticket records using MCP-backed tools. "
                "Supports simple lookups, filtered lists, billing context, and escalation ticket creation."
            ),
            tags=["database", "customer", "records", "tickets", "MCP"],
            examples=[
                "Get customer 5",
                "List active customers",
                "Show open tickets for customer 3",
                "List premium customers and their high-priority tickets",
            ],
        ),
    ],
)

print("Customer Data AgentCard created.")

# =============================================================================
# 2) Support Agent (Specialist – Support & Escalation)
# =============================================================================


support_agent = Agent(
    model=MODEL_NAME,
    name="support_agent",
    instruction="""
You are the Support Agent in a multi-agent customer service system.

You receive:
- The original user query.
- The structured JSON output produced by the Customer Data Agent.

Your job is to turn that JSON into a clear, empathetic, user-facing reply.

YOUR RESPONSIBILITIES
- Handle general customer support questions.
- Explain account, ticket, and billing information in natural language.
- Confirm updates (for example, email changes) that were performed by the data layer.
- For urgent issues, clearly communicate that the request has been escalated and that
  a high-priority ticket has been created.

STRICT RULES
1) Preserve all factual information from the JSON. Do NOT contradict or overwrite it.

2) NEVER invent technical problems or system outages.
   - You MUST NOT say things like "temporary issue", "technical problem",
     "system is down", or "I cannot access your account right now"
     unless the JSON explicitly contains an "error" that says so.
   - If there is an "error" field, explain it briefly and tell the user what they can do next
     (for example, provide a correct ID, try again later, or contact support).

3) Billing escalation queries:
   - When the JSON has "type": "billing_escalation":
     * Acknowledge the double charge / billing problem.
     * Apologize for the inconvenience.
     * Clearly state that a high-priority support ticket has been created and assigned
       to the billing team.
     * Give a simple expectation for follow-up (for example, "within 2–3 business days").
     * DO NOT ask the user for their customer ID again. Assume the backend system has
       enough context to route the ticket.

4) Multi-intent queries ("Update my email and show my ticket history"):
   - When the JSON has "type": "multi_intent":
     * First confirm whether the email was successfully updated (using "email_updated"
       and "new_email").
     * Then summarize the ticket history in a clean, readable format.
     * Make sure both intents are clearly acknowledged.

5) Task allocation query:
   - When the JSON has "type": "task_allocation" or "simple_lookup":
     * Greet the user.
     * Summarize key account fields: name, email, status, and relevant dates.
     * End with an invitation like: "How can I help you today?"

6) Complex / premium ticket reports:
   - For "type": "complex_open_tickets" or "high_priority_premium":
     * Summarize the list of customers and their open/high-priority tickets.
     * Use bullet points or a clear structure so the user can quickly scan the results.
     * If there are no matching tickets, state that clearly (for example,
       "Currently there are no high-priority tickets for premium customers.").

7) Style:
   - Use a friendly, concise, and professional tone.
   - Do NOT show raw JSON, tool names, or internal code snippets.
   - Do NOT expose internal agent names such as "customer_data_agent_remote".
   - Your output should read like a polished support response, not a debug log.
""",
)

support_agent_card = AgentCard(
    name="Support Agent",
    url="http://localhost:9102",
    description=(
        "Support Agent (Specialist). Handles general customer support queries, "
        "uses context from the Customer Data Agent, and explains or escalates "
        "issues to the user in clear language."
    ),
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id="customer_support_handling",
            name="Customer Support Handling",
            description=(
                "Resolves customer support issues using context from the Customer Data Agent, "
                "explains account and ticket information, and acknowledges escalation flows."
            ),
            tags=["support", "helpdesk", "customer-service", "escalation"],
            examples=[
                "Help customer 3 reset their email based on JSON context.",
                "Explain the account status and upgrade eligibility.",
                "Summarize the ticket history for a given customer.",
                "Explain that a billing issue has been escalated with high priority.",
            ],
        ),
    ],
)

print("Support AgentCard created.")

# =============================================================================
# 3) Remote A2A proxies for the two specialist agents
# =============================================================================

customer_data_agent_remote = RemoteA2aAgent(
    name="customer_data_agent_remote",
    description="Remote access to Customer Data Agent via A2A.",
    # Use the new recommended agent-card endpoint
    agent_card="http://localhost:9101/.well-known/agent-card.json",
)

print("Remote Customer Data Agent created.")

support_agent_remote = RemoteA2aAgent(
    name="support_agent_remote",
    description="Remote access to Support Agent via A2A.",
    agent_card="http://localhost:9102/.well-known/agent-card.json",
)

print("Remote Support Agent created.")

# =============================================================================
# 4) Router Agent (Orchestrator – entry point for A2A client)
# =============================================================================
# This Router Agent is implemented as a SequentialAgent:
# - The A2A client sends all user queries only to this Router.
# - The Router first calls the Customer Data Agent (DB + MCP).
# - The Router then feeds the resulting structured JSON to the Support Agent.
# - The final user-facing answer is produced by the Support Agent.
# This satisfies the assignment's "Router / Orchestrator" requirement in an
# explicit two-step multi-agent pipeline.


router_agent = SequentialAgent(
    name="router_agent",
    sub_agents=[
        customer_data_agent_remote,
        support_agent_remote,
    ],
)

print("Router Agent (Sequential Orchestrator) created.")

router_agent_card = AgentCard(
    name="Router Agent",
    url="http://localhost:9200",
    description=(
        "Router Agent (Orchestrator). Entry point of the multi-agent system. "
        "Receives customer queries, delegates data access to the Customer Data "
        "Agent via MCP, then routes enriched context to the Support Agent to "
        "produce the final response. Coordinates task allocation, escalation, "
        "and multi-step workflows required by the assignment."
    ),
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id="routing_and_orchestration",
            name="Routing and Orchestration",
            description=(
                "Understands that different parts of the query are handled by "
                "different specialists. Orchestrates calls to the Customer Data "
                "Agent and Support Agent for simple lookups, coordinated upgrade "
                "help, complex open-ticket queries, billing escalation, "
                "multi-intent requests, and premium-customer reports."
            ),
            tags=["router", "orchestration", "multi-agent"],
            examples=[
                "Get customer information for ID 5",
                "I'm customer 12345 and need help upgrading my account",
                "Show me all active customers who have open tickets",
                "I've been charged twice, please refund immediately",
                "Update my email and show my ticket history",
                "What's the status of all high-priority tickets for premium customers?",
                "Help customer 12—they can't log in",
                "Show open tickets for customer 4",
                "List all disabled customers",
                "Create a ticket for customer 3",
                "I was double charged—help me",
            ],
        ),
    ],
)

print("Router AgentCard created.")
