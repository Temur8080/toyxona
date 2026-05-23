"""Edge AI dan odam sanash va «toy» (tadbir) aniqlash."""
import datetime
import os

import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Max
from django.utils import timezone

from apps.camera.models import Camera
from apps.camera.tasks import run_update_camera_info
from apps.counting.models import HallEvent, PeopleCount
from apps.main.models import Hall

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")


def toy_event_threshold():
    return int(getattr(settings, "TOY_EVENT_THRESHOLD", 12))


def ensure_ai_counting_enabled(hall):
    """Faol onlayn kameralarda AI sanashni yoqish va edge ga yuborish."""
    cams = Camera.objects.filter(
        hall_id=hall.id,
        is_active=True,
        is_online=True,
    ).exclude(device_sn="").exclude(device_sn__isnull=True)

    to_enable = list(cams.filter(use_ai=False).values_list("pk", flat=True))
    if to_enable:
        Camera.objects.filter(pk__in=to_enable).update(use_ai=True)
        for pk in to_enable:
            run_update_camera_info(pk)


def fetch_people_count(hall, camera_by_sn):
    """Edge dan zal bo'yicha odamlar soni (kamera bo'yicha eng yuqori qiymat)."""
    if not hall.server_ip:
        return None, None, None

    host = f"http://{hall.server_ip}:1984"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    try:
        resp = requests.get(f"{host}/api/ai/people-count", headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("total") if data.get("total") is not None else data.get("count")
            if total is not None:
                recorded_at = parse_edge_time(data.get("recorded_at") or data.get("check_at"))
                return int(total), recorded_at, None
    except Exception:
        pass

    after = timezone.localtime() - relativedelta(days=7)
    saved = PeopleCount.objects.filter(hall_id=hall.id).aggregate(
        saved=Max("recorded_at"),
    ).get("saved") or after

    try:
        resp = requests.get(
            f"{host}/api/ai/states",
            params={"saved": saved.isoformat() if saved else ""},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return None, None, None

    per_camera = []
    for sn, states in payload.items():
        camera = camera_by_sn.get(sn)
        if not camera:
            continue
        cam_count = 0
        cam_latest = None
        for state in states:
            check_at = parse_edge_time(state.get("check_at"))
            if cam_latest is None or check_at > cam_latest:
                cam_latest = check_at
            if "count" in state:
                cam_count = max(cam_count, int(state["count"]))
            elif state.get("state") == 0:
                cam_count += 1
        if cam_count > 0:
            per_camera.append((cam_count, cam_latest, camera))

    if not per_camera:
        return None, None, None

    best = max(per_camera, key=lambda row: row[0])
    return best[0], best[1] or timezone.now(), best[2]


def parse_edge_time(value):
    if not value:
        return timezone.now()
    if isinstance(value, datetime.datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value)
    return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def process_toy_event(hall_id, count, recorded_at):
    """Threshold dan oshsa — toy boshlandi; tushsa — tugadi."""
    threshold = toy_event_threshold()
    active = HallEvent.objects.filter(hall_id=hall_id, is_active=True).first()
    recorded_at = recorded_at or timezone.now()

    if count >= threshold:
        if active:
            if count > active.peak_count:
                active.peak_count = count
                active.save(update_fields=["peak_count"])
        else:
            HallEvent.objects.create(
                hall_id=hall_id,
                started_at=recorded_at,
                peak_count=count,
                is_active=True,
            )
    elif active:
        active.is_active = False
        active.ended_at = recorded_at
        active.save(update_fields=["is_active", "ended_at"])


def sync_hall_people_count(hall, *, force=False, enable_ai=True):
    """Bitta toyxona uchun sanash. Returns: (saved, count, message)."""
    if not hall.server_ip:
        return False, None, "server_ip yo'q"

    if enable_ai:
        ensure_ai_counting_enabled(hall)

    cameras = list(Camera.objects.filter(hall_id=hall.id, is_active=True).order_by("id"))
    camera_by_sn = {c.device_sn: c for c in cameras if c.device_sn}

    count, recorded_at, camera = fetch_people_count(hall, camera_by_sn)
    if count is None:
        return False, None, "edge dan ma'lumot yo'q"

    recorded_at = recorded_at or timezone.now()

    if not force:
        last = PeopleCount.objects.filter(hall_id=hall.id).aggregate(last=Max("recorded_at"))["last"]
        if last and recorded_at <= last:
            process_toy_event(hall.id, count, timezone.now())
            return False, count, "allaqachon yangilangan"

    PeopleCount.objects.create(
        hall_id=hall.id,
        camera=camera,
        count=count,
        recorded_at=recorded_at,
    )
    process_toy_event(hall.id, count, recorded_at)
    return True, count, "saqlandi"


def sync_all_halls(*, force=False):
    results = []
    for hall in Hall.objects.order_by("id"):
        if not hall.server_ip:
            continue
        saved, count, msg = sync_hall_people_count(hall, force=force)
        results.append((hall, saved, count, msg))
    return results
