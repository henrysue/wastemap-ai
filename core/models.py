from django.contrib.auth.models import AbstractUser
from django.db import models


class Section(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    latitude = models.FloatField(default=34.0)
    longitude = models.FloatField(default=-118.4)

    def __str__(self):
        return self.name


class Subsection(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='subsections')
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    latitude = models.FloatField(default=34.0)
    longitude = models.FloatField(default=-118.4)

    def __str__(self):
        return f"{self.section.name} - {self.name}"


ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('employee', 'Employee'),
    ('user', 'User'),
]


class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL)
    subsection = models.ForeignKey(Subsection, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


WASTE_TYPE_CHOICES = [
    ('msw', 'Municipal Solid Waste (MSW)'),
    ('hazardous', 'Hazardous Waste'),
    ('organic', 'Organic Waste'),
    ('recyclable', 'Recyclable Waste'),
    ('liquid', 'Liquid Waste'),
    ('ewaste', 'Electronic Waste (E-waste)'),
    ('cd', 'Construction & Demolition Debris'),
    ('medical', 'Medical/Clinical Waste'),
    ('gaseous', 'Gaseous Waste'),
]

PROPERTY_CHOICES = [
    ('biodegradable', 'Biodegradable'),
    ('non_biodegradable', 'Non-biodegradable'),
    ('inert', 'Inert'),
]

REVIEW_STATUS_CHOICES = [
    ('auto', 'Auto'),
    ('pending', 'Pending Review'),
    ('reviewed', 'Reviewed'),
]


class WasteItem(models.Model):
    waste_type = models.CharField(max_length=30, choices=WASTE_TYPE_CHOICES)
    properties = models.CharField(max_length=30, choices=PROPERTY_CHOICES)
    confidence = models.FloatField(default=0.0)
    image_snapshot = models.ImageField(upload_to='snapshots/', null=True, blank=True)
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL)
    subsection = models.ForeignKey(Subsection, null=True, blank=True, on_delete=models.SET_NULL)
    captured_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS_CHOICES, default='auto')
    reviewed_by = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='reviewed_items',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_waste_type_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
