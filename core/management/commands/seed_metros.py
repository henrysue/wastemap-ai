"""Seed metropolitan-area Sections, neighborhood Subsections, and random WasteItems.

Usage:
    python manage.py seed_metros
    python manage.py seed_metros --items-per-subsection 60 --days 120
    python manage.py seed_metros --clear   # wipe existing WasteItems first
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from core.models import Section, Subsection, WasteItem


METROS = [
    {
        'name': 'New York City',
        'lat': 40.7128, 'lng': -74.0060,
        'subs': [
            ('Manhattan',     40.7831, -73.9712),
            ('Brooklyn',      40.6782, -73.9442),
            ('Queens',        40.7282, -73.7949),
            ('The Bronx',     40.8448, -73.8648),
            ('Staten Island', 40.5795, -74.1502),
        ],
    },
    {
        'name': 'Chicago',
        'lat': 41.8781, 'lng': -87.6298,
        'subs': [
            ('The Loop',     41.8786, -87.6251),
            ('Lincoln Park', 41.9214, -87.6513),
            ('Wicker Park',  41.9088, -87.6796),
            ('Hyde Park',    41.7943, -87.5907),
            ('Lakeview',     41.9403, -87.6537),
        ],
    },
    {
        'name': 'San Francisco',
        'lat': 37.7749, 'lng': -122.4194,
        'subs': [
            ('Mission',  37.7599, -122.4148),
            ('SoMa',     37.7785, -122.4056),
            ('Sunset',   37.7521, -122.4942),
            ('Castro',   37.7609, -122.4350),
            ('Marina',   37.8023, -122.4364),
        ],
    },
    {
        'name': 'Seattle',
        'lat': 47.6062, 'lng': -122.3321,
        'subs': [
            ('Capitol Hill', 47.6253, -122.3222),
            ('Ballard',      47.6680, -122.3843),
            ('Fremont',      47.6510, -122.3500),
            ('Queen Anne',   47.6370, -122.3570),
            ('Downtown',     47.6062, -122.3321),
        ],
    },
    {
        'name': 'Boston',
        'lat': 42.3601, 'lng': -71.0589,
        'subs': [
            ('Back Bay',    42.3503, -71.0810),
            ('Cambridge',   42.3736, -71.1097),
            ('South End',   42.3388, -71.0765),
            ('Beacon Hill', 42.3588, -71.0707),
            ('Allston',     42.3539, -71.1337),
        ],
    },
    {
        'name': 'Miami',
        'lat': 25.7617, 'lng': -80.1918,
        'subs': [
            ('South Beach',   25.7907, -80.1300),
            ('Wynwood',       25.8010, -80.1990),
            ('Brickell',      25.7617, -80.1918),
            ('Coral Gables',  25.7215, -80.2684),
            ('Little Havana', 25.7657, -80.2197),
        ],
    },
    {
        'name': 'Houston',
        'lat': 29.7604, 'lng': -95.3698,
        'subs': [
            ('Downtown', 29.7604, -95.3698),
            ('Midtown',  29.7370, -95.3760),
            ('Heights',  29.7990, -95.4111),
            ('Galleria', 29.7370, -95.4613),
            ('Montrose', 29.7440, -95.3905),
        ],
    },
    {
        'name': 'Denver',
        'lat': 39.7392, 'lng': -104.9903,
        'subs': [
            ('LoDo',         39.7517, -104.9999),
            ('Cherry Creek', 39.7185, -104.9536),
            ('Capitol Hill', 39.7351, -104.9762),
            ('RiNo',         39.7700, -104.9810),
            ('Highlands',    39.7613, -105.0190),
        ],
    },
]

WASTE_WEIGHTS = {
    'msw':        0.25,
    'organic':    0.20,
    'recyclable': 0.20,
    'liquid':     0.08,
    'ewaste':     0.07,
    'cd':         0.07,
    'hazardous':  0.05,
    'medical':    0.05,
    'gaseous':    0.03,
}

PROPERTY_WEIGHTS = {
    'biodegradable':     0.40,
    'non_biodegradable': 0.45,
    'inert':             0.15,
}


class Command(BaseCommand):
    help = "Seed metropolitan-area Sections, Subsections, and random WasteItem records."

    def add_arguments(self, parser):
        parser.add_argument(
            '--items-per-subsection', type=int, default=40,
            help='Random WasteItem records to generate per subsection (default 40).',
        )
        parser.add_argument(
            '--days', type=int, default=90,
            help='Spread WasteItem timestamps over the last N days (default 90).',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete existing WasteItem rows before seeding.',
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        sections_new = 0
        subs_new = 0
        for metro in METROS:
            section, created = Section.objects.get_or_create(
                slug=slugify(metro['name']),
                defaults={
                    'name': metro['name'],
                    'latitude': metro['lat'],
                    'longitude': metro['lng'],
                },
            )
            if created:
                sections_new += 1
            for sub_name, lat, lng in metro['subs']:
                _, sub_created = Subsection.objects.get_or_create(
                    section=section,
                    slug=slugify(f"{metro['name']}-{sub_name}"),
                    defaults={
                        'name': sub_name,
                        'latitude': lat,
                        'longitude': lng,
                    },
                )
                if sub_created:
                    subs_new += 1

        self.stdout.write(self.style.SUCCESS(
            f"Geography: +{sections_new} sections, +{subs_new} subsections."
        ))

        if opts['clear']:
            removed, _ = WasteItem.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f"Cleared {removed} existing WasteItem rows."
            ))

        waste_types = list(WASTE_WEIGHTS.keys())
        waste_w = list(WASTE_WEIGHTS.values())
        prop_types = list(PROPERTY_WEIGHTS.keys())
        prop_w = list(PROPERTY_WEIGHTS.values())

        now = timezone.now()
        max_seconds = opts['days'] * 24 * 3600
        items_per_sub = opts['items_per_subsection']

        instances = []
        timestamps = []
        for sub in Subsection.objects.select_related('section'):
            for _ in range(items_per_sub):
                ts = now - timedelta(seconds=random.randint(0, max_seconds))
                timestamps.append(ts)
                instances.append(WasteItem(
                    waste_type=random.choices(waste_types, weights=waste_w, k=1)[0],
                    properties=random.choices(prop_types, weights=prop_w, k=1)[0],
                    confidence=round(random.uniform(0.55, 0.99), 2),
                    section=sub.section,
                    subsection=sub,
                    captured_by=None,
                ))

        WasteItem.objects.bulk_create(instances, batch_size=500)
        # bulk_create's pre_save overwrote timestamp via auto_now_add; restore intended values.
        for inst, ts in zip(instances, timestamps):
            inst.timestamp = ts
        WasteItem.objects.bulk_update(instances, ['timestamp'], batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(instances)} WasteItem rows across "
            f"{Subsection.objects.count()} subsections."
        ))
