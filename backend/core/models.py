from django.contrib.auth import get_user_model
from django.db import models


class Staff(models.Model):
    name = models.CharField(max_length=100)
    office = models.CharField(max_length=100)
    job_title = models.CharField(max_length=100)
    staff_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Asset(models.Model):
    name = models.CharField(max_length=100)
    asset_id = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=100)
    assigned_to = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_assets',
    )
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Assignment(models.Model):
    assignment_id = models.CharField(max_length=100, unique=True)
    asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignment_records',
    )
    assignee = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    date_assigned = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=100)
    approved_by = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.assignment_id


class MaintenanceTicket(models.Model):
    LANE_CHOICES = [
        ('Critical', 'Critical'),
        ('Planned', 'Planned'),
        ('Preventive', 'Preventive'),
    ]

    ticket_id = models.CharField(max_length=100, unique=True)
    lane = models.CharField(max_length=20, choices=LANE_CHOICES)
    asset_ref = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_tickets',
    )
    asset = models.CharField(max_length=200)
    task = models.CharField(max_length=200)
    owner = models.CharField(max_length=100)
    eta = models.CharField(max_length=100)
    status = models.CharField(max_length=40, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.ticket_id


class UserSettings(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='settings')
    display_name = models.CharField(max_length=120, blank=True)
    maintenance_alerts = models.BooleanField(default=True)
    assignment_updates = models.BooleanField(default=True)
    weekly_summary = models.BooleanField(default=False)
    default_office = models.CharField(max_length=100, blank=True)
    report_range = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Settings for {self.user_id}"


class LocationEvent(models.Model):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='location_events',
    )
    location = models.CharField(max_length=200)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='location_events',
    )

    def __str__(self):
        return f"{self.asset.asset_id} @ {self.location}"
