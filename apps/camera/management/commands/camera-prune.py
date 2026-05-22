from django.core.management import BaseCommand

from apps.camera.edge import parse_edge_devices
from apps.camera.models import Camera
from apps.main.models import Hall
import os


class Command(BaseCommand):
    help = "Edge da yo'q (dublikat) kameralarni nofaol qiladi, edge dagilarni faol qiladi."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, default=1)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        token = os.environ.get("CONTROL_ACCESS_TOKEN")
        hall = Hall.objects.get(pk=options["id"])
        edge = parse_edge_devices(hall.server_ip, token)
        edge_sns = {d["device_sn"] for d in edge}
        self.stdout.write(f"Hall: {hall} | Edge SN: {len(edge_sns)}")

        qs = Camera.objects.filter(hall_id=hall.id)
        on_edge = qs.filter(device_sn__in=edge_sns)
        off_edge = qs.exclude(device_sn__in=edge_sns)

        self.stdout.write(f"  DB jami: {qs.count()}")
        self.stdout.write(f"  Edge bilan mos: {on_edge.count()}")
        self.stdout.write(f"  Edge da yo'q (nofaol qilinadi): {off_edge.count()}")

        if options["dry_run"]:
            return

        on_edge.update(is_active=True)
        n = off_edge.update(is_active=False, is_online=False)
        self.stdout.write(self.style.SUCCESS(f"Nofaol qilindi: {n}"))
        self.stdout.write(f"Vebda ko'rinadi (faol): {qs.filter(is_active=True).count()}")
