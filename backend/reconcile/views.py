from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from reconcile.models import Location, SystemARecord, SystemBEntry
from reconcile.compare import compare


class DisagreementsAPIView(APIView):
    """
    GET /api/disagreements/?org=<ORG>&reason=<REASON>&sort=<SORT>
    
    Provides tenant-isolated reconciliation results between System A and System B.
    Tenant safety rules:
    - Strict tenant filtering at the database layer (only queries data belonging to requested org).
    - If a record involves cross-org mismatch (e.g. A in ORG-A, B misrouted to ORG-B),
      external location names are masked as '[Restricted External Location]' to eliminate data leakage.
    """

    def get(self, request, *args, **kwargs):
        org = request.query_params.get("org", "").strip()
        if not org:
            return Response(
                {"error": "Query parameter 'org' is required (e.g. ?org=ORG-A)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Fetch valid locations for this tenant
        tenant_locations = Location.objects.filter(org_id=org)
        tenant_loc_ids = set(tenant_locations.values_list("location_id", flat=True))

        if not tenant_loc_ids:
            return Response(
                {"error": f"Unknown or invalid org: '{org}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Map all locations in DB to org for leak masking
        all_loc_to_org = {loc.location_id: loc.org_id for loc in Location.objects.all()}

        # 2. Query System A records belonging to this tenant's locations
        a_qs = SystemARecord.objects.filter(location__org_id=org)
        a_rows = {}
        for r in a_qs:
            a_rows[r.record_id] = {
                "record_id": r.record_id,
                "location_id": r.location_id,
                "event_date": r.event_date.isoformat(),
                "category_code": r.category_code,
                "actor_id": r.actor_id,
                "base_value": r.base_value,
                "adjustment": r.adjustment,
                "total_value": r.total_value,
                "state": r.state,
            }

        # 3. Query System B entries:
        # Include entries at this tenant's locations OR entries pointing to this tenant's System A records
        tenant_a_record_ids = set(a_rows.keys())
        b_qs = SystemBEntry.objects.filter(
            Q(location__org_id=org) | Q(record_ref__in=tenant_a_record_ids)
        )

        b_rows = []
        for b in b_qs:
            b_rows.append({
                "entry_id": b.entry_id,
                "record_ref": b.record_ref,
                "location_id": b.location_id,
                "recorded_on": b.recorded_on.isoformat(),
                "value": b.value,
                "label": b.label,
            })

        # 4. Run pure reconciliation logic
        disagreements = compare(a_rows, b_rows)

        # 5. Filter out any items that belong to the other org (e.g. orphans located at other org)
        # and sanitize cross-tenant location leaks
        filtered_disagreements = []
        for item in disagreements:
            loc = item.get("location_id")
            # If the item's primary location is not in this tenant's locations, skip it
            if loc not in tenant_loc_ids:
                continue

            # Format Decimal numbers for JSON serialization
            a_val = str(item["a_value"]) if item["a_value"] is not None else None
            b_val = str(item["b_value"]) if item["b_value"] is not None else None
            diff_val = str(item["difference"]) if item["difference"] is not None else None

            # Sanitize details string if it mentions an external location belonging to another org
            details = item.get("details", "")
            for other_loc_id, other_org in all_loc_to_org.items():
                if other_org != org and other_loc_id in details:
                    details = details.replace(other_loc_id, "[Restricted External Location]")

            filtered_disagreements.append({
                "reason": item["reason"],
                "record_id": item["record_id"],
                "location": loc,
                "a_value": a_val,
                "b_value": b_val,
                "difference": diff_val,
                "details": details,
            })

        # 6. Filter by reason if requested
        reason_filter = request.query_params.get("reason", "").strip()
        if reason_filter and reason_filter.upper() != "ALL":
            filtered_disagreements = [
                d for d in filtered_disagreements if d["reason"].upper() == reason_filter.upper()
            ]

        # 7. Sort if requested
        # Support ?sort=value, ?sort=-value, ?sort=difference, ?sort=-difference, ?sort=record_id, etc.
        sort_param = request.query_params.get("sort", "").strip()
        if sort_param:
            reverse = sort_param.startswith("-")
            field = sort_param.lstrip("-")
            # If user sorts by "value" or "-value", map to b_value or a_value
            target_field = "b_value" if field == "value" else field

            def get_sort_key(d):
                val = d.get(target_field)
                if val is None:
                    # Treat None as negative infinity so they sort consistently
                    return Decimal("-999999999999") if target_field in ("a_value", "b_value", "difference") else ""
                if target_field in ("a_value", "b_value", "difference"):
                    try:
                        return Decimal(val)
                    except Exception:
                        return Decimal("-999999999999")
                return str(val)

            filtered_disagreements.sort(key=get_sort_key, reverse=reverse)

        return Response(filtered_disagreements, status=status.HTTP_200_OK)
