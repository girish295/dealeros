from django.db import models


class Location(models.Model):
    """
    The canonical source of truth for location and tenant (org) mapping.
    LOC-101..103 belong to ORG-A.
    LOC-201..202 belong to ORG-B.
    """
    location_id = models.CharField(max_length=50, primary_key=True)
    org_id = models.CharField(max_length=50, db_index=True)
    location_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.location_id} ({self.org_id})"


class SystemARecord(models.Model):
    """
    One row per event as System A recorded it.
    total_value = base_value + adjustment.
    """
    record_id = models.CharField(max_length=50, unique=True, db_index=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='system_a_records')
    event_date = models.DateField()
    category_code = models.CharField(max_length=50)
    actor_id = models.CharField(max_length=50, null=True, blank=True)
    base_value = models.DecimalField(max_digits=12, decimal_places=2)
    adjustment = models.DecimalField(max_digits=12, decimal_places=2)
    total_value = models.DecimalField(max_digits=12, decimal_places=2)
    state = models.CharField(max_length=20)  # CONFIRMED or VOIDED

    def __str__(self):
        return f"{self.record_id} - {self.total_value} ({self.state})"


class SystemBEntry(models.Model):
    """
    One row per entry as System B recorded it.
    Can have multiple entries per System A record (splits or duplicates), or point to non-existent records (orphans).
    Therefore, record_ref is indexed but NOT unique, and NOT a foreign key to SystemARecord.
    """
    entry_id = models.CharField(max_length=50, unique=True, db_index=True)
    record_ref_raw = models.CharField(max_length=100)
    record_ref = models.CharField(max_length=50, db_index=True, null=True, blank=True)  # Cleaned e.g. REC-1034
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='system_b_entries')
    recorded_on = models.DateField()
    value_raw = models.CharField(max_length=100, blank=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # Cleaned Decimal
    label = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.entry_id} -> {self.record_ref} - {self.value}"
