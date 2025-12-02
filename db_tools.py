"""
db_tools.py

High-level database helper functions used as tools by ADK agents.

These helpers wrap the lower-level functions in db.py and return
JSON-friendly dicts with a consistent schema, so that agents can
reason about success / errors more easily.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import sqlite3
from contextlib import closing

# Import the core DB implementation (same DB and schema as MCP server)
from db import (
    DB_PATH,
    _connect,  # type: ignore  # internal helper in db.py
    _row_to_dict,  # type: ignore
    get_customer as db_get_customer,
    list_customers as db_list_customers,
    update_customer as db_update_customer,
    create_ticket as db_create_ticket,
    get_customer_history as db_get_customer_history,
    list_open_tickets as db_list_open_tickets,
)



# --------------------------------------------------------------------
# Helper: JSON-safe conversion
# --------------------------------------------------------------------
def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


# --------------------------------------------------------------------
# Core customer helpers
# --------------------------------------------------------------------
def get_customer(customer_id: int, db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Return a single customer by id.

    Output:
    {
        "success": bool,
        "customer": {...},   # present if success
        "error": "..."       # present if not success
    }
    """
    record = db_get_customer(customer_id, db_path=db_path)
    if record is None:
        return {
            "success": False,
            "error": f"Customer {customer_id} not found.",
        }
    return {
        "success": True,
        "customer": {k: _json_safe(v) for k, v in record.items()},
    }


def list_customers(
    status: Optional[str] = None,
    limit: int = 10,
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """
    List customers, optionally filtered by status.

    Output:
    {
        "success": True,
        "customers": [ {...}, {...}, ... ]
    }
    """
    rows = db_list_customers(status=status, limit=limit, db_path=db_path)
    return {
        "success": True,
        "customers": [{k: _json_safe(v) for k, v in row.items()} for row in rows],
    }


def list_active_customers(
    db_path: Path = DB_PATH,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Convenience wrapper: list all ACTIVE customers.
    """
    rows = db_list_customers(status="active", limit=limit, db_path=db_path)
    return {
        "success": True,
        "customers": [{k: _json_safe(v) for k, v in row.items()} for row in rows],
    }


def list_premium_customers(
    db_path: Path = DB_PATH,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Convenience wrapper: list PREMIUM customers.

    In this demo, customers whose name contains 'Premium' are treated as premium-tier.
    (Matches the seeded data in database_setup.py such as 'Pat Premium'.)
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT *
            FROM customers
            WHERE name LIKE '%Premium%'
            ORDER BY id
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()

    return {
        "success": True,
        "customers": [{k: _json_safe(v) for k, v in row.items()} for row in rows],
    }


def update_customer_email(
    customer_id: int,
    new_email: str,
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """
    Update only the email field for a customer.

    Output:
    {
        "success": bool,
        "customer": {...},   # updated record if success
        "error": "..."       # if failed
    }
    """
    record = db_update_customer(
        customer_id,
        data={"email": new_email},
        db_path=db_path,
    )
    if record is None:
        return {
            "success": False,
            "error": f"Customer {customer_id} not found or update failed.",
        }
    return {
        "success": True,
        "customer": {k: _json_safe(v) for k, v in record.items()},
    }


# --------------------------------------------------------------------
# Ticket helpers
# --------------------------------------------------------------------
def create_ticket(
    customer_id: int,
    issue: str,
    priority: str = "medium",
    status: str = "open",
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """
    Create a new ticket for a customer.

    Output:
    {
        "success": True,
        "ticket": {...}
    }
    """
    ticket = db_create_ticket(
        customer_id=customer_id,
        issue=issue,
        priority=priority,
        status=status,
        db_path=db_path,
    )
    return {
        "success": True,
        "ticket": {k: _json_safe(v) for k, v in ticket.items()},
    }


def get_customer_history(
    customer_id: int,
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """
    Retrieve all tickets for a given customer, newest first.

    Output:
    {
        "success": True,
        "tickets": [ {...}, {...}, ... ]
    }
    """
    history = db_get_customer_history(customer_id, db_path=db_path)
    return {
        "success": True,
        "tickets": [{k: _json_safe(v) for k, v in t.items()} for t in history],
    }


def customer_ticket_history(
    customer_id: int,
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """
    Alias for get_customer_history; some agents expect this tool name.
    """
    return get_customer_history(customer_id=customer_id, db_path=db_path)


def list_open_tickets(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    List all non-resolved tickets ordered by priority and recency.

    Output:
    {
        "success": True,
        "tickets": [ {...}, {...}, ... ]
    }
    """
    rows = db_list_open_tickets(db_path=db_path)
    return {
        "success": True,
        "tickets": [{k: _json_safe(v) for k, v in row.items()} for row in rows],
    }


def open_tickets_for_customer(
    customer_id: int,
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """
    Return all NON-resolved tickets for a specific customer.

    Output:
    {
        "success": True,
        "tickets": [ {...}, {...}, ... ]
    }
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT *
            FROM tickets
            WHERE customer_id = ?
              AND status != 'resolved'
            ORDER BY priority DESC, created_at DESC
            """,
            (customer_id,),
        )
        rows = cur.fetchall()

    return {
        "success": True,
        "tickets": [{k: _json_safe(v) for k, v in row.items()} for row in rows],
    }


def high_priority_tickets_for_customers(
    customer_ids: Optional[List[int]] = None,
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """
    Return HIGH-priority, non-resolved tickets for the given customers.

    If customer_ids is None or empty, return all high-priority, non-resolved tickets.

    Output:
    {
        "success": True,
        "tickets": [ {...}, {...}, ... ]
    }
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        if customer_ids:
            placeholders = ",".join("?" for _ in customer_ids)
            query = f"""
                SELECT *
                FROM tickets
                WHERE status != 'resolved'
                  AND priority = 'high'
                  AND customer_id IN ({placeholders})
                ORDER BY created_at DESC
            """
            cur.execute(query, tuple(customer_ids))
        else:
            cur.execute(
                """
                SELECT *
                FROM tickets
                WHERE status != 'resolved'
                  AND priority = 'high'
                ORDER BY created_at DESC
                """
            )
        rows = cur.fetchall()

    return {
        "success": True,
        "tickets": [{k: _json_safe(v) for k, v in row.items()} for row in rows],
    }


def list_active_customers_with_open_tickets(
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """
    Return all ACTIVE customers who have at least one NON-resolved ticket.

    Output:
    {
        "success": True,
        "customers": [ {...}, {...}, ... ]
    }
    """
    try:
        with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT DISTINCT c.*
                FROM customers c
                JOIN tickets t
                  ON t.customer_id = c.id
                WHERE c.status = 'active'
                  AND t.status != 'resolved'
                ORDER BY c.id
                """
            )
            rows = cur.fetchall()

        return {
            "success": True,
            "customers": [{k: _json_safe(v) for k, v in row.items()} for row in rows],
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Database error in list_active_customers_with_open_tickets: {exc}",
        }



def billing_context_for_customer(
    customer_id: int,
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """
    Return a lightweight 'billing context' for a customer.

    In this demo, we approximate billing context as all tickets for the customer
    whose issue mentions billing / charge / payment.

    Output:
    {
        "success": True,
        "tickets": [ {...}, {...}, ... ]
    }
    """
    keywords = ["billing", "charge", "payment", "invoice"]
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        conditions = " OR ".join("issue LIKE ?" for _ in keywords)
        params: List[Any] = [f"%{kw}%" for kw in keywords]
        params.insert(0, customer_id)  # first param is customer_id

        cur.execute(
            f"""
            SELECT *
            FROM tickets
            WHERE customer_id = ?
              AND ({conditions})
            ORDER BY created_at DESC
            """,
            tuple(params),
        )
        rows = cur.fetchall()

    return {
        "success": True,
        "tickets": [{k: _json_safe(v) for k, v in row.items()} for row in rows],
    }
