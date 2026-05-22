import os

from django.core.management import BaseCommand

from apps.camera.edge import fetch_devices_payload, normalize_edge_device, parse_edge_devices
from apps.main.models import Hall


class Command(BaseCommand):
    help = "Edge /api/devices javobini tekshiradi va kamera sonini ko'rsatadi."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, default=1)

    def handle(self, *args, **options):
        token = os.environ.get("CONTROL_ACCESS_TOKEN")
        hall = Hall.objects.get(pk=options["id"])
        self.stdout.write(f"Hall: {hall} | server_ip: {hall.server_ip}")

        raw_list = fetch_devices_payload(hall.server_ip, token)
        self.stdout.write(f"Raw devices in JSON: {len(raw_list)}")

        for i, raw in enumerate(raw_list[:3]):
            self.stdout.write(f"  [{i}] {normalize_edge_device(raw)}")

        try:
            parsed = parse_edge_devices(hall.server_ip, token)
            self.stdout.write(self.style.SUCCESS(f"Parsed OK: {len(parsed)} devices"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Parse error: {exc}"))

        from apps.camera.models import Camera
        count = Camera.objects.filter(hall_id=hall.id, is_active=True).count()
        self.stdout.write(f"DB active cameras: {count}")
