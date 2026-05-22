from django.core.management import BaseCommand

from apps.camera.models import Camera
from apps.main.models import Hall


class Command(BaseCommand):
    help = "Toyxona bo'yicha kamera statistikasi."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, default=1)

    def handle(self, *args, **options):
        hall = Hall.objects.get(pk=options["id"])
        total = Camera.objects.filter(hall_id=hall.id).count()
        active = Camera.objects.filter(hall_id=hall.id, is_active=True).count()
        inactive = Camera.objects.filter(hall_id=hall.id, is_active=False).count()
        self.stdout.write(f"Hall: {hall}")
        self.stdout.write(f"  Jami DB: {total}")
        self.stdout.write(f"  Faol (vebda): {active}")
        self.stdout.write(f"  Nofaol (yashirin): {inactive}")
