"""Edge serverdan odamlar sonini olish va DB ga yozish."""
import datetime
import os
from typing import Optional, Tuple

import requests
from dateutil.relativedelta import relativedelta
from django.db.models import Max
from django.utils import timezone

from apps.camera.models import Camera
from apps.counting.models import PeopleCount
from apps.main.models import Hall

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")


def parse_edge_time(value):
    if not value:
        return timezone.now()
    if isinstance(value, datetime.datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value)
    return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def fetch_people_count_from_edge(hall, camera_by_sn) -> Tuple[Optional[int], Optional[datetime.datetime], Optional[Camera]]:
    if not hall.server_ip:
        return None, None, None

    host = f"http://{hall.server_ip}:1984"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    try:
        resp = requests.get(f"{host}/api/ai/people-count", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("total") if data.get("total") is not None else data.get("count")
            if total is not None:
                recorded_at = parse_edge_time(data.get("recorded_at") or data.get("check_at"))
                return int(total), recorded_at, None
    except Exception:
        pass

    after = timezone.localtime() - relativedelta(days=7)
    saved = PeopleCount.objects.filter(hall_id=hall.id).aggregate(saved=Max("recorded_at"))["saved"] or after

    try:
        resp = requests.get(
            f"{host}/api/ai/states",
            params={"saved": saved.isoformat() if saved else ""},
            headers=headers,
            timeout=12,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return None, None, None

    total_count = 0
    latest_at = None
    latest_camera = None

    for sn, states in payload.items():
        camera = camera_by_sn.get(sn)
        if not camera:
            continue
        for state in states:
            check_at = parse_edge_time(state.get("check_at"))
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


def sync_people_count_for_hall(hall_id, *, force=False) -> dict:
    """Bitta toyxona uchun edge dan sanash ma'lumotini yuklaydi."""
    try:
        hall = Hall.objects.get(pk=hall_id)
    except Hall.DoesNotExist:
        return {"ok": False, "error": "hall_not_found"}

    if not hall.server_ip:
        return {"ok": False, "error": "no_server_ip"}

    cameras = list(Camera.objects.filter(hall_id=hall.id, is_active=True, use_ai=True).order_by("id"))
    camera_by_sn = {c.device_sn: c for c in cameras if c.device_sn}

    count, recorded_at, camera = fetch_people_count_from_edge(hall, camera_by_sn)
    if count is None:
        return {"ok": False, "error": "no_edge_data", "ai_cameras": len(cameras)}

    last = PeopleCount.objects.filter(hall_id=hall.id).order_by("-recorded_at").first()
    if last and not force:
        if recorded_at < last.recorded_at:
            return {"ok": True, "skipped": True, "count": last.count, "recorded_at": last.recorded_at}
        if recorded_at == last.recorded_at and count == last.count:
            return {"ok": True, "skipped": True, "count": last.count, "recorded_at": last.recorded_at}

    row = PeopleCount.objects.create(
        hall_id=hall.id,
        camera=camera,
        count=count,
        recorded_at=recorded_at,
    )
    return {
        "ok": True,
        "saved": True,
        "count": row.count,
        "recorded_at": row.recorded_at,
        "ai_cameras": len(cameras),
    }
