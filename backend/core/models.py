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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ticket_id
