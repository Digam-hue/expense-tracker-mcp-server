from fastmcp import FastMCP
import os
import libsql_client

TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
    raise RuntimeError(
        "TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be set as environment variables."
    )

mcp = FastMCP("ExpenseTracker")

# Created lazily, on first use, inside the server's own running event loop.
# Creating it eagerly at import time fails with "no running event loop"
# because the async HTTP client needs a loop that doesn't exist yet at that point.
client = None
_db_initialized = False

async def get_ready_client():
    global client, _db_initialized
    if client is None:
        client = libsql_client.create_client(url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
    if not _db_initialized:
        try:
            await client.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)
            _db_initialized = True
            print("Turso database initialized successfully")
        except Exception as e:
            print(f"Database initialization error: {e}")
            raise
    return client

@mcp.tool()
async def add_expense(date, amount, category, subcategory="", note=""):
    '''Add a new expense entry to the database.'''
    try:
        c = await get_ready_client()
        rs = await c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            [date, amount, category, subcategory, note]
        )
        return {"status": "success", "id": rs.last_insert_rowid, "message": "Expense added successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

@mcp.tool()
async def list_expenses(start_date, end_date):
    '''List expense entries within an inclusive date range.'''
    try:
        c = await get_ready_client()
        rs = await c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date DESC, id DESC
            """,
            [start_date, end_date]
        )
        return [dict(zip(rs.columns, row)) for row in rs.rows]
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}

@mcp.tool()
async def summarize(start_date, end_date, category=None):
    '''Summarize expenses by category within an inclusive date range.'''
    try:
        query = """
            SELECT category, SUM(amount) AS total_amount, COUNT(*) as count
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY total_amount DESC"

        c = await get_ready_client()
        rs = await c.execute(query, params)
        return [dict(zip(rs.columns, row)) for row in rs.rows]
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}

@mcp.resource("expense:///categories", mime_type="application/json")
def categories():
    try:
        default_categories = {
            "categories": [
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Business",
                "Other"
            ]
        }

        try:
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            import json
            return json.dumps(default_categories, indent=2)
    except Exception as e:
        return f'{{"error": "Could not load categories: {str(e)}"}}'

# Start the server
if __name__ == "__main__":
    # Render (and most PaaS platforms) inject the port to bind via the PORT env var.
    # Falls back to 8000 for local runs.
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
