import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Asset, Assignment, MaintenanceTicket, Staff


class Command(BaseCommand):
    help = "Seed dummy staff, assets, assignments, and maintenance tickets."

    def add_arguments(self, parser):
        parser.add_argument("--staff", type=int, default=25, help="Number of staff records to create.")
        parser.add_argument("--assets", type=int, default=80, help="Number of asset records to create.")
        parser.add_argument("--assignments", type=int, default=40, help="Number of assignment records to create.")
        parser.add_argument("--tickets", type=int, default=30, help="Number of maintenance tickets to create.")
        parser.add_argument("--clear", action="store_true", help="Delete existing records before seeding.")

    def handle(self, *args, **options):
        if options["clear"]:
            Assignment.objects.all().delete()
            MaintenanceTicket.objects.all().delete()
            Asset.objects.all().delete()
            Staff.objects.all().delete()

        staff_count = max(0, options["staff"])
        asset_count = max(0, options["assets"])
        assignment_count = max(0, options["assignments"])
        ticket_count = max(0, options["tickets"])

        staff_created = self._seed_staff(staff_count)
        asset_created = self._seed_assets(asset_count)
        assignment_created = self._seed_assignments(assignment_count)
        ticket_created = self._seed_tickets(ticket_count)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {staff_created} staff, {asset_created} assets, "
            f"{assignment_created} assignments, {ticket_created} tickets."
        ))

    def _seed_staff(self, count):
        if count == 0:
            return 0

        first_names = [
            "Abiola", "Ada", "Ifeoma", "Tunde", "Chinedu", "Casey", "David", "Noah",
            "Riley", "Jada", "Omar", "Kemi", "Sade", "Liam", "Zara", "Emeka",
        ]
        last_names = [
            "Adegboruwa", "Okeke", "Balogun", "Nwosu", "Luo", "Kim", "Patel",
            "Ibrahim", "Watson", "Ricotti", "Mensah", "Okoro",
        ]
        offices = ["HQ", "Operations", "Network", "Data Center", "HR", "Support", "Field Office"]
        roles = ["IT Support", "Network Engineer", "Analyst", "Admin", "Intern", "Tech Lead"]

        existing_ids = set(Staff.objects.values_list("staff_id", flat=True))
        base_index = Staff.objects.count() + 1
        rows = []
        created = 0

        while created < count:
            staff_id = f"{base_index + created:04d}"
            if staff_id in existing_ids:
                created += 1
                continue
            rows.append(Staff(
                name=f"{random.choice(first_names)} {random.choice(last_names)}",
                office=random.choice(offices),
                job_title=random.choice(roles),
                staff_id=staff_id,
            ))
            created += 1

        Staff.objects.bulk_create(rows)
        return len(rows)

    def _seed_assets(self, count):
        if count == 0:
            return 0

        asset_names = [
            "Dell Latitude 7420", "HP EliteBook 850", "MacBook Pro", "Lenovo ThinkPad X1",
            "Cisco Catalyst 9200", "Netgear Switch", "Surface Laptop", "iPad Air",
            "Logitech Dock", "Epson Workforce", "Samsung Monitor", "HP LaserJet",
        ]
        locations = ["HQ", "Data Center", "Floor 2", "Floor 3", "Remote", "Warehouse"]
        statuses = ["Good condition", "In Repair", "Lost", "Critical Alert"]

        existing_ids = set(Asset.objects.values_list("asset_id", flat=True))
        base_index = Asset.objects.count() + 100
        rows = []
        created = 0
        staff_ids = list(Staff.objects.values_list("id", flat=True))

        while created < count:
            asset_id = f"AS-{base_index + created:04d}"
            if asset_id in existing_ids:
                created += 1
                continue
            assigned_to = random.choice(staff_ids) if staff_ids and random.random() < 0.7 else None
            rows.append(Asset(
                name=random.choice(asset_names),
                asset_id=asset_id,
                location=random.choice(locations),
                status=random.choice(statuses),
                assigned_to_id=assigned_to,
            ))
            created += 1

        Asset.objects.bulk_create(rows)
        return len(rows)

    def _seed_assignments(self, count):
        if count == 0:
            return 0

        assets = list(Asset.objects.all())
        staff = list(Staff.objects.all())
        if not assets:
            return 0

        statuses = ["Active", "In Review", "Returned"]
        rows = []
        start_index = Assignment.objects.count() + 1

        for idx in range(count):
            asset = random.choice(assets)
            assignee = random.choice(staff) if staff else None
            status = random.choice(statuses)
            days_ago = random.randint(0, 180)
            date_assigned = timezone.now().date() - timedelta(days=days_ago)
            return_date = None
            if status == "Returned":
                return_date = date_assigned + timedelta(days=random.randint(1, 30))

            assignment_id = f"AS-{date_assigned:%Y%m%d}-{start_index + idx:04d}"
            rows.append(Assignment(
                assignment_id=assignment_id,
                asset=asset,
                assignee=assignee,
                date_assigned=date_assigned,
                return_date=return_date,
                status=status,
                approved_by="",
            ))

        Assignment.objects.bulk_create(rows)
        return len(rows)

    def _seed_tickets(self, count):
        if count == 0:
            return 0

        assets = list(Asset.objects.all())
        lanes = ["Critical", "Planned", "Preventive"]
        tasks = [
            "Battery replacement", "Firmware update", "Diagnostics", "Port stability testing",
            "Quarterly maintenance", "Screen replacement", "Fan cleaning",
        ]
        owners = ["Network Team", "Ops Team", "Support", "Field Ops"]

        rows = []
        start_index = MaintenanceTicket.objects.count() + 1

        for idx in range(count):
            lane = random.choice(lanes)
            asset = random.choice(assets) if assets else None
            task = random.choice(tasks)
            owner = random.choice(owners)
            eta = (timezone.now() + timedelta(days=random.randint(0, 14))).strftime("%b %d %H:%M")
            ticket_id = f"{'PM' if lane == 'Preventive' else 'M'}-{start_index + idx:04d}"
            asset_label = asset.name if asset else "General Infrastructure"

            rows.append(MaintenanceTicket(
                ticket_id=ticket_id,
                lane=lane,
                asset_ref=asset,
                asset=asset_label,
                task=task,
                owner=owner,
                eta=eta,
            ))

        MaintenanceTicket.objects.bulk_create(rows)
        return len(rows)
