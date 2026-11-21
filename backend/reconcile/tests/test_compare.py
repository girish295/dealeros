from decimal import Decimal
import pytest
from reconcile.compare import compare
from reconcile.importer import normalize_ref, parse_amount


def test_clean_row_produces_no_disagreement():
    """Matching pair of A and B records produces zero disagreements."""
    a = {
        "REC-1001": {
            "record_id": "REC-1001",
            "total_value": Decimal("100.00"),
            "location_id": "LOC-101",
            "event_date": "2026-03-01",
            "state": "CONFIRMED",
        }
    }
    b = [
        {
            "entry_id": "ENT-1",
            "record_ref": "REC-1001",
            "value": Decimal("100.00"),
            "location_id": "LOC-101",
            "recorded_on": "2026-03-01",
            "label": "Standard entry",
        }
    ]
    assert compare(a, b) == []


def test_missing_in_b():
    """System A record with no corresponding entry in B is flagged as MISSING_IN_B."""
    a = {
        "REC-1015": {
            "record_id": "REC-1015",
            "total_value": Decimal("41095.33"),
            "location_id": "LOC-103",
            "event_date": "2026-04-02",
            "state": "CONFIRMED",
        }
    }
    b = []
    res = compare(a, b)
    assert len(res) == 1
    assert res[0]["reason"] == "MISSING_IN_B"
    assert res[0]["record_id"] == "REC-1015"
    assert res[0]["a_value"] == Decimal("41095.33")
    assert res[0]["b_value"] is None


def test_orphan_in_b():
    """System B entry referencing an unknown A record is flagged as ORPHAN_IN_B."""
    a = {}
    b = [
        {
            "entry_id": "ENT/2026/4901",
            "record_ref": "REC-1999",
            "value": Decimal("41250.00"),
            "location_id": "LOC-102",
            "recorded_on": "2026-03-18",
            "label": "Orphan entry",
        }
    ]
    res = compare(a, b)
    assert len(res) == 1
    assert res[0]["reason"] == "ORPHAN_IN_B"
    assert res[0]["record_id"] == "REC-1999"
    assert res[0]["b_value"] == Decimal("41250.00")
    assert res[0]["a_value"] is None


def test_duplicate_in_b():
    """Multiple B entries that do NOT sum up to A total are flagged as DUPLICATE_IN_B."""
    a = {
        "REC-1042": {
            "record_id": "REC-1042",
            "total_value": Decimal("112837.06"),
            "location_id": "LOC-101",
            "event_date": "2026-03-04",
            "state": "CONFIRMED",
        }
    }
    b = [
        {
            "entry_id": "ENT-1",
            "record_ref": "REC-1042",
            "value": Decimal("112837.06"),
            "location_id": "LOC-101",
            "recorded_on": "2026-03-04",
        },
        {
            "entry_id": "ENT-2",
            "record_ref": "REC-1042",
            "value": Decimal("112837.06"),
            "location_id": "LOC-101",
            "recorded_on": "2026-03-04",
        },
    ]
    res = compare(a, b)
    assert len(res) == 1
    assert res[0]["reason"] == "DUPLICATE_IN_B"
    assert res[0]["record_id"] == "REC-1042"
    assert res[0]["b_value"] == Decimal("225674.12")


def test_split_that_sums_is_not_an_error():
    """Two B entries summing exactly to A total (e.g. part 1 & 2) is a valid split, NOT an error."""
    a = {
        "REC-1055": {
            "record_id": "REC-1055",
            "total_value": Decimal("179877.32"),
            "location_id": "LOC-103",
            "event_date": "2026-03-14",
            "state": "CONFIRMED",
        }
    }
    b = [
        {
            "entry_id": "ENT/2026/4055",
            "record_ref": "REC-1055",
            "value": Decimal("71950.93"),
            "location_id": "LOC-103",
            "recorded_on": "2026-03-14",
            "label": "Entry for CAT-08",
        },
        {
            "entry_id": "ENT/2026/4903",
            "record_ref": "REC-1055",
            "value": Decimal("107926.39"),
            "location_id": "LOC-103",
            "recorded_on": "2026-03-14",
            "label": "Entry part 2 of 2",
        },
    ]
    # Sum: 71950.93 + 107926.39 == 179877.32
    assert compare(a, b) == []


def test_value_mismatch():
    """Different amounts in single A and B records are flagged as VALUE_MISMATCH."""
    a = {
        "REC-1003": {
            "record_id": "REC-1003",
            "total_value": Decimal("121388.01"),
            "location_id": "LOC-102",
            "event_date": "2026-03-24",
            "state": "CONFIRMED",
        }
    }
    b = [
        {
            "entry_id": "ENT/2026/4003",
            "record_ref": "REC-1003",
            "value": Decimal("94834.38"),
            "location_id": "LOC-102",
            "recorded_on": "2026-03-24",
        }
    ]
    res = compare(a, b)
    assert len(res) == 1
    assert res[0]["reason"] == "VALUE_MISMATCH"
    assert res[0]["record_id"] == "REC-1003"
    assert res[0]["a_value"] == Decimal("121388.01")
    assert res[0]["b_value"] == Decimal("94834.38")
    assert res[0]["difference"] == Decimal("26553.63")


def test_blank_value_is_flagged_not_zero():
    """A blank value in B is stored as None (never 0) and flagged as VALUE_MISMATCH."""
    a = {
        "REC-1050": {
            "record_id": "REC-1050",
            "total_value": Decimal("160405.85"),
            "location_id": "LOC-102",
            "event_date": "2026-03-18",
            "state": "CONFIRMED",
        }
    }
    b = [
        {
            "entry_id": "ENT/2026/4050",
            "record_ref": "REC-1050",
            "value": parse_amount(""),  # Parsed as None
            "location_id": "LOC-102",
            "recorded_on": "2026-03-18",
        }
    ]
    res = compare(a, b)
    assert len(res) == 1
    assert res[0]["reason"] == "VALUE_MISMATCH"
    assert res[0]["b_value"] is None
    assert res[0]["b_value"] != Decimal("0.00")


def test_messy_reference_formats_match_cleanly():
    """Raw reference strings like 'rec1034', ' REC - 1070 ', and '1112' normalize and match."""
    raw_refs = ["rec1034", " REC - 1070 ", "1112"]
    expected = ["REC-1034", "REC-1070", "REC-1112"]
    for raw, exp in zip(raw_refs, expected):
        assert normalize_ref(raw) == exp

    # Test Indian currency format
    assert parse_amount("1,25,400.00") == Decimal("125400.00")


def test_location_mismatch():
    """Different location between A and B is flagged as LOCATION_MISMATCH."""
    a = {
        "REC-1077": {
            "record_id": "REC-1077",
            "total_value": Decimal("50000.00"),
            "location_id": "LOC-102",
            "event_date": "2026-03-20",
            "state": "CONFIRMED",
        }
    }
    b = [
        {
            "entry_id": "ENT/2026/4077",
            "record_ref": "REC-1077",
            "value": Decimal("50000.00"),
            "location_id": "LOC-201",
            "recorded_on": "2026-03-20",
        }
    ]
    res = compare(a, b)
    assert len(res) == 1
    assert res[0]["reason"] == "LOCATION_MISMATCH"
    assert res[0]["record_id"] == "REC-1077"


def test_date_mismatch():
    """Different date between A and B is flagged as DATE_MISMATCH."""
    a = {
        "REC-1009": {
            "record_id": "REC-1009",
            "total_value": Decimal("50000.00"),
            "location_id": "LOC-101",
            "event_date": "2026-03-31",
            "state": "CONFIRMED",
        }
    }
    b = [
        {
            "entry_id": "ENT/2026/4009",
            "record_ref": "REC-1009",
            "value": Decimal("50000.00"),
            "location_id": "LOC-101",
            "recorded_on": "2026-04-02",
        }
    ]
    res = compare(a, b)
    assert len(res) == 1
    assert res[0]["reason"] == "DATE_MISMATCH"
    assert res[0]["record_id"] == "REC-1009"


def test_voided_record_with_active_entry_in_b():
    """A VOIDED record in System A that has active B entries is flagged."""
    a = {
        "REC-1019": {
            "record_id": "REC-1019",
            "total_value": Decimal("57092.35"),
            "location_id": "LOC-202",
            "event_date": "2026-04-05",
            "state": "VOIDED",
        }
    }
    b = [
        {
            "entry_id": "ENT/2026/4019",
            "record_ref": "REC-1019",
            "value": Decimal("57092.35"),
            "location_id": "LOC-202",
            "recorded_on": "2026-04-05",
        }
    ]
    res = compare(a, b)
    assert any(r["reason"] == "VOIDED_RECORD_ACTIVE_IN_B" for r in res)
