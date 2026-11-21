import csv
import logging
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Any, Tuple

from reconcile.models import Location, SystemARecord, SystemBEntry

logger = logging.getLogger(__name__)


def normalize_ref(raw: str) -> str | None:
    """
    Normalizes dirty record reference strings to standard format 'REC-XXXX'.
    Examples:
        'rec1034'        -> 'REC-1034'
        ' REC - 1070 '   -> 'REC-1070'
        '1112'           -> 'REC-1112'
        'REC-1015'       -> 'REC-1015'
    Returns None if no digits are found.
    """
    m = re.search(r"\d+", (raw or "").strip())
    return f"REC-{m.group()}" if m else None


def parse_amount(raw: str) -> Decimal | None:
    """
    Parses currency strings into Decimal numbers.
    Handles Indian number commas ('1,25,400.00' -> Decimal('125400.00')).
    Blank or unparseable junk returns None, NEVER 0.
    """
    s = (raw or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        logger.warning(f"Invalid decimal value: {raw}")
        return None


def clean_cell(val: Any) -> str:
    """Strips leading and trailing whitespace from string cells."""
    if val is None:
        return ""
    return str(val).strip()


def import_dataset(data_dir: Path | str) -> Dict[str, Any]:
    """
    Imports locations.csv, system_a.csv, and system_b.csv from data_dir.
    Guaranteed idempotent (uses update_or_create on unique keys).
    Preserves all dirty rows, never drops or crashes.
    """
    data_path = Path(data_dir)
    loc_file = data_path / "locations.csv"
    a_file = data_path / "system_a.csv"
    b_file = data_path / "system_b.csv"

    stats = {
        "locations_read": 0,
        "locations_saved": 0,
        "a_read": 0,
        "a_saved": 0,
        "b_read": 0,
        "b_saved": 0,
        "b_values_left_empty": 0,
        "b_refs_cleaned": 0,
    }

    # 1. Import Locations
    with open(loc_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["locations_read"] += 1
            loc_id = clean_cell(row.get("location_id"))
            org_id = clean_cell(row.get("org_id"))
            name = clean_cell(row.get("location_name", loc_id))
            Location.objects.update_or_create(
                location_id=loc_id,
                defaults={"org_id": org_id, "location_name": name},
            )
            stats["locations_saved"] += 1

    # Cache location objects for fast lookup
    locations_by_id = {loc.location_id: loc for loc in Location.objects.all()}

    # 2. Import System A
    with open(a_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["a_read"] += 1
            rec_id = clean_cell(row.get("record_id"))
            loc_id = clean_cell(row.get("location_id"))
            loc = locations_by_id.get(loc_id)
            if not loc:
                logger.error(f"Unknown location {loc_id} for System A record {rec_id}")

            actor_id = clean_cell(row.get("actor_id")) or None
            base_val = parse_amount(row.get("base_value"))
            adj_val = parse_amount(row.get("adjustment"))
            tot_val = parse_amount(row.get("total_value"))

            SystemARecord.objects.update_or_create(
                record_id=rec_id,
                defaults={
                    "location": loc,
                    "event_date": clean_cell(row.get("event_date")),
                    "category_code": clean_cell(row.get("category_code")),
                    "actor_id": actor_id,
                    "base_value": base_val,
                    "adjustment": adj_val,
                    "total_value": tot_val,
                    "state": clean_cell(row.get("state")),
                },
            )
            stats["a_saved"] += 1

    # 3. Import System B
    with open(b_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["b_read"] += 1
            entry_id = clean_cell(row.get("entry_id"))
            raw_ref = clean_cell(row.get("record_ref"))
            cleaned_ref = normalize_ref(raw_ref)

            if cleaned_ref != raw_ref:
                stats["b_refs_cleaned"] += 1

            loc_id = clean_cell(row.get("location_id"))
            loc = locations_by_id.get(loc_id)
            if not loc:
                logger.error(f"Unknown location {loc_id} for System B entry {entry_id}")

            raw_val = clean_cell(row.get("value"))
            cleaned_val = parse_amount(raw_val)

            if cleaned_val is None:
                stats["b_values_left_empty"] += 1

            SystemBEntry.objects.update_or_create(
                entry_id=entry_id,
                defaults={
                    "record_ref_raw": raw_ref,
                    "record_ref": cleaned_ref,
                    "location": loc,
                    "recorded_on": clean_cell(row.get("recorded_on")),
                    "value_raw": raw_val,
                    "value": cleaned_val,
                    "label": clean_cell(row.get("label")),
                },
            )
            stats["b_saved"] += 1

    return stats
