from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from reconcile.importer import import_dataset


class Command(BaseCommand):
    help = "Import locations.csv, system_a.csv, and system_b.csv idempotently into SQLite."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=str,
            default=str(settings.BASE_DIR / "data"),
            help="Path to directory containing locations.csv, system_a.csv, system_b.csv",
        )

    def handle(self, *args, **options):
        data_dir = options["data_dir"]
        self.stdout.write(f"Starting import from {data_dir}...")
        stats = import_dataset(data_dir)

        self.stdout.write(self.style.SUCCESS(
            f"Import complete:\n"
            f"  Locations: {stats['locations_read']} read, {stats['locations_saved']} saved\n"
            f"  System A: {stats['a_read']} read, {stats['a_saved']} saved\n"
            f"  System B: {stats['b_read']} read, {stats['b_saved']} saved\n"
            f"  Values left empty: {stats['b_values_left_empty']}\n"
            f"  References cleaned: {stats['b_refs_cleaned']}"
        ))

        # Sanity check
        if stats['locations_read'] != stats['locations_saved']:
            self.stderr.write(self.style.ERROR("Mismatch in locations read vs saved!"))
        if stats['a_read'] != stats['a_saved']:
            self.stderr.write(self.style.ERROR("Mismatch in System A read vs saved!"))
        if stats['b_read'] != stats['b_saved']:
            self.stderr.write(self.style.ERROR("Mismatch in System B read vs saved!"))
