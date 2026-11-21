import pytest
from rest_framework.test import APIClient
from reconcile.importer import import_dataset
from django.conf import settings


@pytest.fixture(scope="session")
def loaded_db(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        import_dataset(settings.BASE_DIR / "data")


@pytest.mark.django_db
def test_api_missing_org_returns_400():
    client = APIClient()
    response = client.get("/api/disagreements/")
    assert response.status_code == 400
    assert "org" in response.data.get("error", "").lower()


@pytest.mark.django_db
def test_api_invalid_org_returns_404():
    client = APIClient()
    response = client.get("/api/disagreements/?org=NON_EXISTENT")
    assert response.status_code == 404


@pytest.mark.django_db
def test_api_returns_org_a_disagreements(loaded_db):
    client = APIClient()
    response = client.get("/api/disagreements/?org=ORG-A")
    assert response.status_code == 200
    data = response.data
    assert isinstance(data, list)
    assert len(data) > 0

    reasons = [item["reason"] for item in data]
    assert "MISSING_IN_B" in reasons
    assert "ORPHAN_IN_B" in reasons
    assert "DUPLICATE_IN_B" in reasons
    assert "VALUE_MISMATCH" in reasons


@pytest.mark.django_db
def test_api_reason_filter(loaded_db):
    client = APIClient()
    response = client.get("/api/disagreements/?org=ORG-A&reason=VALUE_MISMATCH")
    assert response.status_code == 200
    for item in response.data:
        assert item["reason"] == "VALUE_MISMATCH"


@pytest.mark.django_db
def test_api_sorting(loaded_db):
    client = APIClient()
    response = client.get("/api/disagreements/?org=ORG-A&sort=-difference")
    assert response.status_code == 200
    # Values should be non-increasing for non-null differences
    diffs = [float(item["difference"]) for item in response.data if item["difference"] is not None]
    assert diffs == sorted(diffs, reverse=True)


@pytest.mark.django_db
def test_tenant_isolation_org_a_never_sees_org_b(loaded_db):
    """
    CRITICAL REQUIREMENT:
    Assert that calling the API as ORG-A never returns any row with ORG-B location (LOC-201, LOC-202).
    """
    client = APIClient()
    response = client.get("/api/disagreements/?org=ORG-A")
    assert response.status_code == 200
    
    org_b_locations = {"LOC-201", "LOC-202"}
    for item in response.data:
        # Check location field
        assert item["location"] not in org_b_locations, f"Leaked ORG-B location in {item}"
        # Check details string
        for b_loc in org_b_locations:
            assert b_loc not in item.get("details", ""), f"Leaked ORG-B location name in details: {item}"


@pytest.mark.django_db
def test_tenant_isolation_org_b_never_sees_org_a(loaded_db):
    """
    CRITICAL REQUIREMENT:
    Assert that calling the API as ORG-B never returns any row with ORG-A location (LOC-101, LOC-102, LOC-103).
    """
    client = APIClient()
    response = client.get("/api/disagreements/?org=ORG-B")
    assert response.status_code == 200

    org_a_locations = {"LOC-101", "LOC-102", "LOC-103"}
    for item in response.data:
        assert item["location"] not in org_a_locations, f"Leaked ORG-A location in {item}"
        for a_loc in org_a_locations:
            assert a_loc not in item.get("details", ""), f"Leaked ORG-A location name in details: {item}"
