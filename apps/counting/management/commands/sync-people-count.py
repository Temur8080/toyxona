import datetime
import os

import requests
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db.models import Count, Max
from django.utils import timezone

from apps.camera.models import Camera
from apps.counting.models import PeopleCount
from apps.main.models import Hall

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")


class Command(BaseCommand):
    help = "Edge serverdan odamlar sonini yuklab oladi (/api/ai/states yoki /api/ai/people-count)"

    def handle(self, *args, **options):
        for hall in Hall.objects.order_by('id').all():
            if not hall.server_ip:
                continue

            print("Checking", hall, "...")
            host = f"http://{hall.server_ip}:1984"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            cameras = list(Camera.objects.filter(hall_id=hall.id, is_active=True).order_by('id'))
            camera_by_sn = {cam.device_sn: cam for cam in cameras if cam.device_sn}

            count, recorded_at, camera = self.fetch_people_count(host, headers, camera_by_sn)
            if count is None:
                print("\tno data")
                continue

            last = PeopleCount.objects.filter(hall_id=hall.id).aggregate(last=Max('recorded_at'))['last']
            if last and recorded_at <= last:
                print("\talready synced")
                continue

            PeopleCount.objects.create(
                hall_id=hall.id,
                camera=camera,
                count=count,
                recorded_at=recorded_at,
            )
            print(f"\tsaved: {count} at {recorded_at}")

    def fetch_people_count(self, host, headers, camera_by_sn):
        # Yangi edge API: { "total": 42, "recorded_at": "..." }
        try:
            resp = requests.get(f"{host}/api/ai/people-count", headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total") or data.get("count")
                if total is not None:
                    recorded_at = self.parse_time(data.get("recorded_at") or data.get("check_at"))
                    return int(total), recorded_at, None
        except Exception:
            pass

        # Mavjud API: /api/ai/states — zonalar bo'yicha count yoki band ROI lar
        after = timezone.localtime() - relativedelta(days=7)
        saved = PeopleCount.objects.filter(
            hall_id__in=[cam.hall_id for cam in camera_by_sn.values()] or [0]
        ).aggregate(saved=Max("recorded_at")).get("saved") or after

        try:
            resp = requests.get(
                f"{host}/api/ai/states",
                params={"saved": saved.isoformat() if saved else ""},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print("\terror", str(e)[:80])
            return None, None, None

        total_count = 0
        latest_at = None
        latest_camera = None

        for sn, states in payload.items():
            camera = camera_by_sn.get(sn)
            if not camera:
                continue

            for state in states:
                check_at = self.parse_time(state.get("check_at"))
                if latest_at is None or check_at > latest_at:
                    latest_at = check_at
                    latest_camera = camera

                if "count" in state:
                    total_count = max(total_count, int(state["count"]))
                elif state.get("state") == 0:
                    total_count += 1

        if latest_at is None:
            return None, None, None

        return total_count, latest_at, latest_camera

    @staticmethod
    def parse_time(value):
        if not value:
            return timezone.now()
        if isinstance(value, datetime.datetime):
            return value if timezone.is_aware(value) else timezone.make_aware(value)
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
