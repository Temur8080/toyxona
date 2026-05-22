import os

from django.core.management import BaseCommand

from apps.camera.edge import fetch_devices_payload, normalize_edge_device, parse_edge_devices
from apps.camera.models import Camera
from apps.main.models import Hall


class Command(BaseCommand):
    help = "Toyxona bo'yicha kamera statistikasi (--edge: Edge API tekshiruvi)."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, default=1)
        parser.add_argument(
            "--edge",
            action="store_true",
            help="Edge /api/devices javobini ham ko'rsatadi",
        )

    def handle(self, *args, **options):
        hall = Hall.objects.get(pk=options["id"])
        total = Camera.objects.filter(hall_id=hall.id).count()
        active = Camera.objects.filter(hall_id=hall.id, is_active=True).count()
        inactive = Camera.objects.filter(hall_id=hall.id, is_active=False).count()
        self.stdout.write(f"Hall: {hall} | server_ip: {hall.server_ip}")
        self.stdout.write(f"  Jami DB: {total}")
        self.stdout.write(f"  Faol (vebda): {active}")
        self.stdout.write(f"  Nofaol (yashirin): {inactive}")

        if not options["edge"]:
            return

        token = os.environ.get("CONTROL_ACCESS_TOKEN")
        raw_list = fetch_devices_payload(hall.server_ip, token)
        self.stdout.write(f"Edge raw devices: {len(raw_list)}")
        for i, raw in enumerate(raw_list[:3]):
            self.stdout.write(f"  [{i}] {normalize_edge_device(raw)}")
        try:
            parsed = parse_edge_devices(hall.server_ip, token)
            self.stdout.write(self.style.SUCCESS(f"Edge parsed: {len(parsed)} devices"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Edge parse error: {exc}"))
