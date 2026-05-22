from django.core.management import BaseCommand

from apps.camera.models import Camera
from apps.camera.tasks import sync_camera_info
from apps.main.models import Hall
from toyxona.security import switch_to_www_data


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--id',
            type=int,
            default=0,
            help='Force update snapshots',
        )

    def handle(self, *args, **options):
        switch_to_www_data()

        Hall_id = options.get('id')

        qs = Hall.objects.order_by('id')
        if Hall_id > 0:
            qs = qs.filter(id=Hall_id)

        for Hall in qs.all():
            print(Hall)
            cameras = Camera.objects.filter(Hall=Hall).order_by("id").all()

            for camera in cameras:
                sync_camera_info(camera, timeout = 5)


