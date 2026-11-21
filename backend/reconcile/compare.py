"""
Pure Python reconciliation logic.
Completely decoupled from Django models, ORM, and HTTP layers for fast, isolated unit testing.
"""

from decimal import Decimal
from typing import Dict, List, Any, Optional


def compare(a_rows: Dict[str, Dict[str, Any]], b_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Matches System A records against System B entries and flags disagreements.

    Args:
        a_rows: Mapping of record_id -> {
            'record_id': str,
            'total_value': Decimal,
            'location_id': str,
            'event_date': str | date,
            'state': str ('CONFIRMED' or 'VOIDED'),
            ...
        }
        b_rows: List of dicts representing System B entries: [
            {
                'entry_id': str,
                'record_ref': str (normalized, e.g. 'REC-1034'),
                'value': Decimal | None,
                'location_id': str,
                'recorded_on': str | date,
                'label': str,
                ...
            }
        ]

    Returns:
        List of disagreement dicts:
        {
            'reason': str,
            'record_id': str,
            'location_id': str,
            'a_value': Optional[Decimal],
            'b_value': Optional[Decimal],
            'difference': Optional[Decimal],
            'details': str,
        }
    """
    disagreements: List[Dict[str, Any]] = []

    # 1. Group System B entries by cleaned record_ref
    by_ref: Dict[str, List[Dict[str, Any]]] = {}
    for entry in b_rows:
        ref = entry.get("record_ref")
        if ref:
            by_ref.setdefault(ref, []).append(entry)
        else:
            # Entry with no reference at all is an orphan
            disagreements.append({
                "reason": "ORPHAN_IN_B",
                "record_id": entry.get("entry_id", "UNKNOWN"),
                "location_id": entry.get("location_id"),
                "a_value": None,
                "b_value": entry.get("value"),
                "difference": None,
                "details": f"System B entry {entry.get('entry_id')} has no record reference.",
            })

    # 2. Check for Orphans in B (B points to record_id not found in System A)
    for ref, entries in by_ref.items():
        if ref not in a_rows:
            for e in entries:
                disagreements.append({
                    "reason": "ORPHAN_IN_B",
                    "record_id": ref,
                    "location_id": e.get("location_id"),
                    "a_value": None,
                    "b_value": e.get("value"),
                    "difference": None,
                    "details": f"System B entry {e.get('entry_id')} references non-existent System A record {ref}.",
                })

    # 3. Walk through each System A record
    for rid, a in a_rows.items():
        entries = by_ref.get(rid, [])
        a_total = a.get("total_value")
        a_loc = a.get("location_id")
        a_date = str(a.get("event_date")) if a.get("event_date") else None
        a_state = a.get("state", "CONFIRMED")

        # Check MISSING_IN_B
        if not entries:
            disagreements.append({
                "reason": "MISSING_IN_B",
                "record_id": rid,
                "location_id": a_loc,
                "a_value": a_total,
                "b_value": None,
                "difference": a_total,
                "details": f"System A record {rid} has no corresponding entries in System B.",
            })
            continue

        # Check VOIDED in System A with active entries in System B
        if a_state == "VOIDED":
            b_sum = sum((e.get("value") for e in entries if e.get("value") is not None), Decimal("0.00"))
            disagreements.append({
                "reason": "VOIDED_RECORD_ACTIVE_IN_B",
                "record_id": rid,
                "location_id": a_loc,
                "a_value": Decimal("0.00"),
                "b_value": b_sum,
                "difference": -b_sum,
                "details": f"Record {rid} is VOIDED in System A, but has active recorded entries in System B.",
            })

        # Check for Blank / None values in System B entries
        vals = [e.get("value") for e in entries]
        if any(v is None for v in vals):
            disagreements.append({
                "reason": "VALUE_MISMATCH",
                "record_id": rid,
                "location_id": a_loc,
                "a_value": a_total,
                "b_value": None,
                "difference": None,
                "details": f"Record {rid} contains a blank/missing value in System B.",
            })
            continue

        # Multiple entries in B: check split vs duplicate
        if len(entries) > 1:
            total_b = sum(vals, Decimal("0.00"))
            if total_b != a_total:
                # Does NOT add up to A's total -> DUPLICATE_IN_B
                diff = a_total - total_b if a_total is not None else None
                disagreements.append({
                    "reason": "DUPLICATE_IN_B",
                    "record_id": rid,
                    "location_id": a_loc,
                    "a_value": a_total,
                    "b_value": total_b,
                    "difference": diff,
                    "details": f"Record {rid} has {len(entries)} entries in System B totaling {total_b}, mismatching System A total {a_total}.",
                })
            # If total_b == a_total, it is a valid split (e.g. part 1 of 2 + part 2 of 2) -> NOT an error!
            continue

        # Single entry in B
        e = entries[0]
        b_val = e.get("value")
        b_loc = e.get("location_id")
        b_date = str(e.get("recorded_on")) if e.get("recorded_on") else None

        # Value comparison (against total_value)
        if b_val != a_total:
            diff = (a_total - b_val) if (a_total is not None and b_val is not None) else None
            disagreements.append({
                "reason": "VALUE_MISMATCH",
                "record_id": rid,
                "location_id": a_loc,
                "a_value": a_total,
                "b_value": b_val,
                "difference": diff,
                "details": f"Value mismatch for {rid}: System A total is {a_total}, System B value is {b_val}.",
            })

        # Location mismatch check
        if b_loc != a_loc:
            disagreements.append({
                "reason": "LOCATION_MISMATCH",
                "record_id": rid,
                "location_id": a_loc,
                "a_value": a_total,
                "b_value": b_val,
                "difference": Decimal("0.00") if a_total == b_val else (a_total - b_val if a_total and b_val else None),
                "details": f"Location mismatch for {rid}: System A recorded {a_loc}, System B recorded {b_loc}.",
            })

        # Date mismatch check
        if b_date != a_date:
            disagreements.append({
                "reason": "DATE_MISMATCH",
                "record_id": rid,
                "location_id": a_loc,
                "a_value": a_total,
                "b_value": b_val,
                "difference": Decimal("0.00") if a_total == b_val else (a_total - b_val if a_total and b_val else None),
                "details": f"Date mismatch for {rid}: System A date is {a_date}, System B date is {b_date}.",
            })

    return disagreements
