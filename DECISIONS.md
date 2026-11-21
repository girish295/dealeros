# Technical Decisions (DECISIONS.md)

## Decision: Compare System B's value against System A's total_value
- **Rejected:** Compare against `base_value`.
- **Why:** In System A, `total_value` is explicitly calculated as `base_value + adjustment`. In almost all matched rows, System B's values match `total_value`, not `base_value`.

## Decision: Preserve blank or dirty values as null / None
- **Rejected:** Coerce blank or invalid entries to `0` or `0.00`.
- **Why:** Blank indicates unknown or missing ledger data, whereas `0.00` is a valid financial quantity (e.g. zero balance). Coercing to zero corrupts reconciliation audit trails.

## Decision: Normalize dirty reference formats with digit regex
- **Rejected:** Require strict string matching on `record_ref`.
- **Why:** System B includes dirty inputs such as `rec1034`, ` REC - 1070 `, and `1112`. Normalizing with `r"\d+"` to `REC-{digits}` cleanly matches all genuine records without dropping rows.

## Decision: Treat multiple entries that sum to total as valid split entries
- **Rejected:** Flag any record with multiple entries as a duplicate.
- **Why:** Real accounting ledgers often split transactions across multiple line items (e.g. `REC-1055` has labels indicating "part 2 of 2" that sum up exactly to System A's total). Only entries that do not sum to total are duplicates.

## Decision: Flag VOIDED records with active entries in System B
- **Rejected:** Treat active entries for VOIDED records as normal matches or ignore them.
- **Why:** In `REC-1019`, System A voided the transaction while System B kept an active ledger entry. Flagging this as `VOIDED_RECORD_ACTIVE_IN_B` gives auditors immediate visibility into orphaned financial exposure.

## Decision: Sanitize and mask cross-tenant location data on the trap row
- **Rejected:** Expose the other tenant's location ID or drop the row entirely.
- **Why:** For record `REC-1077`, System A recorded `LOC-102` (`ORG-A`), but System B misrouted it to `LOC-201` (`ORG-B`). Exposing `LOC-201` to an `ORG-A` user violates tenant privacy boundaries. We display the record to `ORG-A` but mask external branch identifiers as `[Restricted External Location]`.

## Decision: Include Date and Location differences as configurable disagreement reasons
- **Rejected:** Discard metadata differences and only flag monetary mismatches.
- **Why:** Financial audits require ledger entries to align not just on money, but also on accounting period (date) and cost center (location).

## Decision: Use Decimal and DecimalField instead of Float
- **Rejected:** Python `float` and Django `FloatField`.
- **Why:** Binary floating-point arithmetic introduces IEEE 754 precision errors (e.g. `0.1 + 0.2 != 0.3`). Financial reconciliation requires exact decimal precision.

## Decision: Decouple comparison engine into pure Python functions
- **Rejected:** Couple comparison logic directly into Django ORM queries or REST view handlers.
- **Why:** Pure functions can be tested in milliseconds without database setup, enabling comprehensive unit testing across all edge cases.

## Decision: Use SQLite for zero-friction evaluation
- **Rejected:** PostgreSQL, MySQL, or Docker.
- **Why:** SQLite ships with Python, runs immediately on clean clones, supports ACID transactions, and eliminates setup hurdles for reviewers.
