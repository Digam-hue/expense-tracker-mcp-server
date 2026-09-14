# Expense Tracker MCP Server

A simple **MCP (Model Context Protocol) server** that lets an AI assistant (like Claude) add, list, and summarize your personal expenses — backed by a persistent Turso (libSQL) database, deployed on Render.

Instead of manually opening a spreadsheet, you can just tell your AI assistant things like *"Add ₹500 for food"* or *"Show my expenses this month"*, and it calls this server to actually store and fetch the data.

---

## What is MCP?

**MCP (Model Context Protocol)** is an open standard that lets AI assistants call external tools over a common interface. An MCP server exposes a set of **tools** (functions) that the assistant can invoke, with typed inputs and structured outputs.

In this project:
- The assistant "sees" three tools: `add_expense`, `list_expenses`, `summarize`.
- When you ask something in plain language, the assistant picks the right tool, fills in the parameters, and calls this server.
- This server runs the actual database logic and returns a structured JSON result back to the assistant.

This means the assistant doesn't need to know how the database works — it just needs to know what tools are available and what they do.

---

## What this server does

Built with [FastMCP](https://github.com/jlowin/fastmcp) (a Python framework for building MCP servers) and [Turso](https://turso.tech/) (a hosted libSQL/SQLite database) for storage.

### Tools

| Tool | Purpose | Parameters |
|---|---|---|
| `add_expense` | Adds a new expense entry | `date`, `amount`, `category`, `subcategory` (optional), `note` (optional) |
| `list_expenses` | Lists all expenses in a date range | `start_date`, `end_date` |
| `summarize` | Totals and counts expenses per category in a date range | `start_date`, `end_date`, `category` (optional) |

### Resource

- `expense:///categories` — returns the list of available expense categories as JSON (read from `categories.json`, falling back to a default list if missing).

### Data stored per expense

- `id` — auto-incrementing primary key
- `date` — expense date
- `amount` — expense amount
- `category` — e.g. Food, Travel, Personal Care
- `subcategory` — optional finer detail (e.g. "Haircut")
- `note` — optional free-text note

---

## How it works, step by step

1. **Database**: On first use, the server connects to a Turso database and creates the `expenses` table if it doesn't already exist.
2. **Adding an expense**: The `add_expense` tool inserts a row into the `expenses` table and returns the new row's ID.
3. **Listing expenses**: The `list_expenses` tool queries all rows between two dates (inclusive), most recent first.
4. **Summarizing**: The `summarize` tool groups expenses by category within a date range, returning the total amount and entry count per category (optionally filtered to a single category).
5. **Serving over HTTP**: The server runs with `mcp.run(transport="http", ...)`, binding to the port Render provides via the `PORT` environment variable (defaults to `8000` locally).

---

## Project structure

```
expense-tracker-mcp-server/
├── main.py            # Server entry point — defines the MCP tools and resource
├── categories.json    # Default list of expense categories
├── pyproject.toml     # Project metadata and dependencies
├── requirements.txt   # Pip-installable dependency list
├── uv.lock            # Locked dependency versions (uv package manager)
└── src/                # Additional source files
```

---

## Setup

### 1. Prerequisites
- Python 3.10+
- A [Turso](https://turso.tech/) database (free tier works fine)
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### 2. Clone the repo
```bash
git clone https://github.com/Digam-hue/expense-tracker-mcp-server.git
cd expense-tracker-mcp-server
```

### 3. Set environment variables
Create a `.env` file or export these directly:
```bash
export TURSO_DATABASE_URL="libsql://<your-db>.turso.io"
export TURSO_AUTH_TOKEN="<your-auth-token>"
```
These are required — the server will refuse to start without them.

### 4. Install dependencies
```bash
uv sync
# or
pip install -r requirements.txt
```

### 5. Run locally
```bash
python main.py
```
By default it serves on `http://0.0.0.0:8000`.

### 6. Deploy (this project uses Render)
- Push the repo to GitHub.
- Create a new **Web Service** on [Render](https://render.com/), pointing at this repo.
- Add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` as environment variables in Render's dashboard.
- Render automatically sets `PORT`; no changes needed for that.

---

## Connecting it to an AI assistant

Once deployed, add the server's URL (e.g. `https://your-app.onrender.com/mcp`) as an MCP connector in your assistant's settings. Once connected, you can just talk naturally:

- "Add ₹500 for food"
- "Show my expenses this month"
- "Summarize spending by category"

The assistant will call `add_expense`, `list_expenses`, or `summarize` accordingly and show you the result.

---

## Notes

- All amounts are stored as-is with no currency conversion — pick one currency and stick to it.
- Categories are freeform strings; `categories.json` is just a suggested list, not an enforced schema.
- The database client is created lazily on first request (inside the server's event loop) to avoid async setup issues at import time.
