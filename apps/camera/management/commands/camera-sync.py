import os

import requests
from django.core.management import BaseCommand

from apps.camera.models import Camera
from apps.camera.tasks import sync_camera_info
from apps.main.models import Hall
from toyxona.security import switch_to_www_data

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")

class Command(BaseCommand):
    def handle(self, *args, **options):
        switch_to_www_data()

        qs = Hall.objects.order_by('id')
        for Hall in qs.all():
            print("")
            print("-" * 30)
            print("Hall:", Hall)
            print("-" * 30)
            print()

            try:
                url = f"http://{Hall.server_ip}:1984/api/version"
                resp = requests.get(url, headers={
                    "Authorization": f"Bearer {ACCESS_TOKEN}"
                }, timeout=5)
                print("\tVersion:", resp.text)
            except Exception as e:
                print("\tException:", str(e))
                continue

            cameras = Camera.objects.prefetch_related("Hall").filter(Hall_id=Hall.id).order_by("id").all()

            for cam in cameras:
                try:
                    sync_camera_info(cam, 2)
                except Exception as e:
                    print("\tException:", str(e))
