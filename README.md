# DealerOS - Financial Ledger Reconciliation Web App

A full-stack reconciliation application that imports and compares financial ledgers recorded across two distinct systems (System A and System B), identifies discrepancies, and displays them in a clean, filterable, and sortable interface with strict multi-tenant data isolation.

---

## 1. How to Run (Clean Clone Instructions)

### Prerequisites
- Python 3.11+
- Node.js 18+ (tested on Node v20/v24)
- Git

### Step-by-Step Setup

#### A. Backend Setup
```bash
# 1. Navigate to the repository
cd dealeros

# 2. Create and activate a Python virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Run database migrations
cd backend
python manage.py migrate

# 5. Import the CSV datasets (Idempotent)
python manage.py import_data

# 6. Run the automated test suite (Unit tests + API + Tenant Isolation)
pytest

# 7. Start the backend development server (runs on http://127.0.0.1:8000)
python manage.py runserver
```

#### B. Frontend Setup (in a separate terminal)
```bash
# 1. Navigate to the frontend directory
cd dealeros/frontend

# 2. Install Node dependencies
npm install

# 3. Start Vite dev server (runs on http://localhost:5173)
npm run dev
```

Open your browser at **http://localhost:5173** to use the reconciliation interface.

---

## 2. What Was Built
- **Robust Idempotent Importer (`backend/reconcile/importer.py`)**:
  - Reads `locations.csv`, `system_a.csv`, and `system_b.csv` with zero dropped rows.
  - Normalizes reference variants (`rec1034`, ` REC - 1070 `, `1112` $\rightarrow$ `REC-XXXX`).
  - Converts Indian comma numbers (`1,25,400.00` $\rightarrow$ `Decimal('125400.00')`).
  - Stores blanks and corrupt data as `null` / `None` (never `0.00`).
  - Ensures exact 120 System A and 121 System B records survive via `update_or_create`.
- **Decoupled Reconciliation Engine (`backend/reconcile/compare.py`)**:
  - Pure Python functions free of ORM and HTTP dependencies for instant execution and testing.
  - Flags: `MISSING_IN_B`, `ORPHAN_IN_B`, `DUPLICATE_IN_B`, `VALUE_MISMATCH`, `LOCATION_MISMATCH`, `DATE_MISMATCH`, and `VOIDED_RECORD_ACTIVE_IN_B`.
  - Intelligently recognizes valid splits (multiple B lines summing to A total) and avoids false positives.
- **Tenant-Safe REST API (`backend/reconcile/views.py`)**:
  - Endpoint: `GET /api/disagreements/?org=ORG-A&reason=...&sort=...`.
  - Strict database-level tenant boundary filtering.
  - Cross-tenant data masking for the trap row (`REC-1077`) to prevent location leakage.
- **Interactive UI Table (`frontend/src/App.jsx`)**:
  - Organization switcher (`ORG-A` / `ORG-B`).
  - Reason filter dropdown.
  - Clickable sorting on System A Value, System B Value, and Difference.
  - Formatted empty cells (`—`) for missing amounts, never showing `0` or `null`.
- **Automated Test Suite (`backend/reconcile/tests/`)**:
  - 18 tests covering every disagreement rule, split recognition, messy formatting, and tenant isolation.

---

## 3. What Was Deliberately Not Built
To stay within the assessment scope and time box, the following were intentionally omitted:
- **User Authentication / Passwords / JWT**: The brief explicitly stated that login and auth are not graded. An organization selector dropdown was used instead.
- **Docker / Containerization**: Evaluators need to test clean clones with native Python and npm commands without container overhead.
- **Heavy UI Frameworks / Complex CSS**: Focused on a plain, correct, readable table with clear semantic badges rather than excessive styling.
- **Complex Pagination**: The dataset has ~120 rows per system, so fast in-memory client/server filtering was prioritized over pagination complexity.

---

## 4. How I Worked with the AI Agent
- **Workflow**: Built milestone by milestone following the assessment plan:
  1. Wrote an audit script first to independently count rows, blanks, and data quirks in each CSV before writing models.
  2. Prompted the agent for isolated pure functions (normalizer, amount parser, comparison logic) and verified each function against real CSV snippets.
  3. Added pytest tests for every individual reason before wiring up the web framework.
  4. Tested the API endpoint for tenant leakage before writing the frontend table.
- **Verification**: Every row count (`A: 120`, `B: 121`, `Locations: 5`) was checked via SQL and Django shell after each run to ensure no rows were dropped or duplicated.

---

## 5. The Three Answers

### a. One thing the AI agent got wrong. How did you notice?
During early test discovery, Django's default `startapp reconcile` command created an empty `reconcile/tests.py` file while we had organized our test suite into a directory `reconcile/tests/test_compare.py`. When running `pytest`, pytest raised an `import file mismatch` error during module collection because both `reconcile.tests` module and `reconcile/tests/` package existed simultaneously. I noticed the error output in terminal, immediately identified the namespace conflict, and removed the redundant `tests.py` file to restore clean test discovery.

### b. The part you are least confident about, and why
The handling of the cross-tenant trap row (`REC-1077`). In this record, System A lists the location as `LOC-102` (`ORG-A`), but System B records it as `LOC-201` (`ORG-B`). While our implementation successfully prevents data leakage by attributing the record to ORG-A and sanitizing external location names to `[Restricted External Location]`, in a real-world enterprise setting this represents an ambiguous boundary dispute: did System B misroute a payment belonging to ORG-A, or did System A erroneously book a transaction belonging to ORG-B? A complete solution would require a dedicated inter-company reconciliation workflow.

### c. If you had a second day, what would you fix first?
I would implement an interactive **Audit Resolution Workflow**: allowing financial operators to click an individual disagreement row to initiate an audit note, attach supporting documentation, or trigger an automated ledger correction entry into System B (e.g. an adjustment credit/debit for `VALUE_MISMATCH` or a reversal for `DUPLICATE_IN_B`), complete with an exportable audit report in CSV format.
