from django.core.management.base import BaseCommand

from apps.counting.services import sync_people_count_for_hall
from apps.main.models import Hall


class Command(BaseCommand):
    help = "Edge serverdan odamlar sonini yuklab oladi (/api/ai/people-count yoki /api/ai/states)"

    def add_arguments(self, parser):
        parser.add_argument("--hall", type=int, help="Faqat bitta toyxona ID")
        parser.add_argument("--force", action="store_true", help="Oxirgi yozuv bilan bir xil bo'lsa ham saqlash")

    def handle(self, *args, **options):
        qs = Hall.objects.order_by("id")
        if options.get("hall"):
            qs = qs.filter(pk=options["hall"])

        for hall in qs:
            if not hall.server_ip:
                continue
            print("Checking", hall, "...")
            result = sync_people_count_for_hall(hall.id, force=options.get("force"))
            if not result.get("ok"):
                print("\t", result.get("error", "failed"), f"(AI kameralar: {result.get('ai_cameras', '?')})")
            elif result.get("skipped"):
                print("\talready up to date:", result.get("count"))
            elif result.get("saved"):
                print("\tsaved:", result.get("count"), "@", result.get("recorded_at"))
