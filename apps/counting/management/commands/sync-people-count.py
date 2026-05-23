from django.core.management.base import BaseCommand

from apps.counting.services import sync_all_halls, toy_event_threshold


class Command(BaseCommand):
    help = "Edge AI: odam sanash + toy (>= threshold) aniqlash"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Vaqt tekshiruvsiz yangilash")
        parser.add_argument("--hall", type=int, help="Faqat bitta toyxona id")

    def handle(self, *args, **options):
        from apps.main.models import Hall
        from apps.counting.services import sync_hall_people_count

        threshold = toy_event_threshold()
        self.stdout.write(f"Toy threshold: >= {threshold} odam")

        if options.get("hall"):
            hall = Hall.objects.get(pk=options["hall"])
            saved, count, msg = sync_hall_people_count(hall, force=options["force"])
            self.stdout.write(f"{hall}: {msg} count={count} saved={saved}")
            return

        for hall, saved, count, msg in sync_all_halls(force=options["force"]):
            self.stdout.write(f"{hall}: {msg} count={count} saved={saved}")
