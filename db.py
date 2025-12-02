import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Base paths used by database_setup.py
DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "customer_service.db"


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Open a SQLite connection with a row factory that returns sqlite3.Row.
    This function also ensures that the data directory exists.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a single sqlite3.Row into a plain Python dict."""
    return {k: row[k] for k in row.keys()}


def _rows_to_list(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Convert an iterable of sqlite3.Row into a list of dicts."""
    return [_row_to_dict(r) for r in rows]


# -----------------------------------------------------------------------------
# Basic customer helpers (kept for backwards compatibility)
# -----------------------------------------------------------------------------


def get_customer(customer_id: int, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """
    Return a single customer by ID, or None if not found.
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = cur.fetchone()
        return _row_to_dict(row) if row else None


def list_customers(
    status: Optional[str] = None,
    limit: int = 10,
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Return a list of customers ordered by creation time (most recent first).

    Parameters
    ----------
    status : optional status filter (e.g. 'active').
    limit  : maximum number of rows to return.
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        if status:
            cur.execute(
                """
                SELECT * FROM customers
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM customers
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cur.fetchall()
        return _rows_to_list(rows)


def update_customer(
    customer_id: int,
    data: Dict[str, Any],
    db_path: Path = DB_PATH,
) -> Optional[Dict[str, Any]]:
    """
    Update basic customer fields (name, email, phone, status) and return
    the updated customer record. If no valid fields are provided, the
    function simply returns the current record.
    """
    if not data:
        return get_customer(customer_id, db_path=db_path)

    valid_fields = {"name", "email", "phone", "status"}
    updates = {k: v for k, v in data.items() if k in valid_fields}
    if not updates:
        return get_customer(customer_id, db_path=db_path)

    columns = ", ".join(f"{k} = ?" for k in updates.keys())
    values: List[Any] = list(updates.values()) + [customer_id]

    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            f"""
            UPDATE customers
            SET {columns}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )
        conn.commit()

    return get_customer(customer_id, db_path=db_path)


# Convenience helper for email updates (useful for multi-intent scenario).
def update_customer_email(
    customer_id: int,
    new_email: str,
    db_path: Path = DB_PATH,
) -> Optional[Dict[str, Any]]:
    """
    Update only the customer's email and return the updated record.
    """
    return update_customer(customer_id, {"email": new_email}, db_path=db_path)


# -----------------------------------------------------------------------------
# Ticket helpers
# -----------------------------------------------------------------------------


def create_ticket(
    customer_id: int,
    issue: str,
    priority: str = "medium",
    status: str = "open",
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """
    Create a new ticket for the given customer and return the created row.
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            INSERT INTO tickets (customer_id, issue, status, priority, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (customer_id, issue, status, priority),
        )
        conn.commit()
        ticket_id = cur.lastrowid
        cur.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = cur.fetchone()
        return _row_to_dict(row)


def get_customer_history(
    customer_id: int,
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Return all tickets for a given customer, ordered by creation time descending.
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT * FROM tickets
            WHERE customer_id = ?
            ORDER BY created_at DESC
            """,
            (customer_id,),
        )
        rows = cur.fetchall()
        return _rows_to_list(rows)


def list_open_tickets(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """
    Return all non-resolved tickets ordered by priority and creation time.
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT * FROM tickets
            WHERE status != 'resolved'
            ORDER BY priority DESC, created_at DESC
            """
        )
        rows = cur.fetchall()
        return _rows_to_list(rows)


def list_open_tickets_for_customer(
    customer_id: int,
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Return all open (non-resolved) tickets for a single customer.
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT * FROM tickets
            WHERE customer_id = ?
              AND status != 'resolved'
            ORDER BY priority DESC, created_at DESC
            """,
            (customer_id,),
        )
        rows = cur.fetchall()
        return _rows_to_list(rows)


def list_high_priority_tickets_for_customers(
    customer_ids: Iterable[int],
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Return all high-priority, non-resolved tickets for a set of customer IDs.
    This is used in the "premium customers high-priority tickets" scenario.
    """
    ids = list(customer_ids)
    if not ids:
        return []

    placeholders = ", ".join("?" for _ in ids)
    query = f"""
        SELECT * FROM tickets
        WHERE customer_id IN ({placeholders})
          AND status != 'resolved'
          AND priority = 'high'
        ORDER BY created_at DESC
    """

    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(query, ids)
        rows = cur.fetchall()
        return _rows_to_list(rows)


def list_billing_tickets_for_customer(
    customer_id: int,
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """
    A simple approximation of "billing context" using tickets.

    This function returns tickets whose issue text suggests billing problems
    (contains words like 'bill', 'billing', 'charge', 'payment').
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT * FROM tickets
            WHERE customer_id = ?
              AND (
                  LOWER(issue) LIKE '%bill%' OR
                  LOWER(issue) LIKE '%charge%' OR
                  LOWER(issue) LIKE '%payment%'
              )
            ORDER BY created_at DESC
            """,
            (customer_id,),
        )
        rows = cur.fetchall()
        return _rows_to_list(rows)


# -----------------------------------------------------------------------------
# Higher-level helpers used by multi-agent scenarios
# -----------------------------------------------------------------------------


def list_active_customers(
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Return all active customers.
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT * FROM customers
            WHERE status = 'active'
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
        return _rows_to_list(rows)


def list_premium_customers(
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Return all premium customers.

    The schema does not have an explicit 'tier' column, so for this
    assignment we treat the synthetic customer with ID 12345 as premium.
    If you later add a real 'tier' or 'is_premium' column, update this
    query accordingly.
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT * FROM customers
            WHERE id = 12345
            """
        )
        rows = cur.fetchall()
        return _rows_to_list(rows)


def list_active_customers_with_open_tickets(
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Return all customers who are ACTIVE and have at least one NON-resolved ticket.

    This is used to answer queries like:
    'Show me all active customers who have open tickets.'
    """
    with closing(_connect(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT DISTINCT c.*
            FROM customers c
            JOIN tickets t ON c.id = t.customer_id
            WHERE c.status = 'active'
              AND t.status != 'resolved'
            ORDER BY c.id
            """
        )
        rows = cur.fetchall()
        return [_row_to_dict(r) for r in rows]