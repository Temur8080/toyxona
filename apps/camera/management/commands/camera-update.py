import os

from django.core.management import BaseCommand
from django.db import transaction

from apps.camera.tasks import sync_cameras
from apps.main.models import Hall
from toyxona.security import switch_to_www_data


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force update snapshots')
        parser.add_argument('--no-snapshots', action='store_true', help='Skip slow snapshot download')
        parser.add_argument('--id', type=int, default=0, help='Hall id')

    def handle(self, *args, **options):
        switch_to_www_data()
        force = options.get('force')
        hall_id = options.get('id')

        with transaction.atomic():
            qs = Hall.objects.select_for_update().order_by('id')
            if hall_id > 0:
                qs = qs.filter(id=hall_id)

            for hall in qs.all():
                if not hall.server_ip:
                    continue
                print("-" * 30)
                print(hall, "checking ...")
                sync_cameras(
                    hall.id,
                    force_update=force,
                    skip_snapshots=options.get('no_snapshots'),
                )
