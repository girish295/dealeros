# Data Audit Notes (DealerOS Assessment)

## 1. Overview of CSV Files
- **`locations.csv`** (5 rows + header = 6 lines):
  - `LOC-101`, `LOC-102`, `LOC-103` $\rightarrow$ `ORG-A`
  - `LOC-201`, `LOC-202` $\rightarrow$ `ORG-B`
  - Only source of tenant mapping.
- **`system_a.csv`** (120 rows + header):
  - Key columns: `record_id`, `location_id`, `event_date`, `category_code`, `actor_id`, `base_value`, `adjustment`, `total_value`, `state`
  - Math check: `base_value + adjustment == total_value` holds for all 120 rows.
  - Empty fields: `actor_id` has 1 blank cell (stored as null).
  - States: 119 `CONFIRMED`, 1 `VOIDED` (`REC-1019`).
- **`system_b.csv`** (121 rows + header):
  - Key columns: `entry_id`, `record_ref`, `location_id`, `recorded_on`, `value`, `label`
  - Extra row count explained: contains duplicates, splits, and orphans.

## 2. Identified Data Anomalies & Dirty Inputs
1. **Reference Normalization Needed (3 rows in B)**:
   - `rec1034` $\rightarrow$ normalized to `REC-1034`
   - ` REC - 1070 ` $\rightarrow$ normalized to `REC-1070`
   - `1112` $\rightarrow$ normalized to `REC-1112`
   - Regex extraction: `r"\d+"` mapped to `REC-{digits}`.
2. **Value Formatting Quirks in B (2 rows)**:
   - Blank value in `REC-1050`: must be stored as `None`/`null` (never as 0.00).
   - Indian comma numbering: `1,25,400.00` in `REC-1064`: parsed as `Decimal("125400.00")`.
3. **Missing Entries in B (2 rows in A)**:
   - `REC-1015` (`LOC-103`, `ORG-A`)
   - `REC-1061` (`LOC-202`, `ORG-B`)
4. **Orphan Entries in B (1 row in B)**:
   - `ENT/2026/4901` points to non-existent `REC-1999` (`LOC-102`, `ORG-A`).
5. **Multiple B Entries for One A Record (2 records)**:
   - `REC-1042`: Two entries with 112,837.06 each (Sum = 225,674.12 vs A total 112,837.06) $\rightarrow$ Real duplicate (`DUPLICATE_IN_B`).
   - `REC-1055`: Two entries (71,950.93 + 107,926.39 = 179,877.32 == A total 179,877.32 with "part 2 of 2") $\rightarrow$ Valid split (NOT an error).
6. **Value Mismatches**:
   - `REC-1003`, `REC-1027`, `REC-1050` (blank), `REC-1064`, `REC-1088`.
7. **Cross-Tenant Trap Row**:
   - `REC-1077`: System A assigns it to `LOC-102` (`ORG-A`), but System B assigns it to `LOC-201` (`ORG-B`).
   - Cross-org leak protection required: ORG-A must not see `LOC-201` or ORG-B branch topology.
8. **Date & Location Mismatches**:
   - Date mismatch: `REC-1009` (A: 2026-03-31, B: 2026-04-02).
   - Location mismatch: `REC-1077`.
9. **Voided Record**:
   - `REC-1019` is marked `VOIDED` in System A, but System B has an active confirmed entry for it (`ENT/2026/4019`).
