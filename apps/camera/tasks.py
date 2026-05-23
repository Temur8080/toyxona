import datetime
import json
import os
from contextlib import ExitStack

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.camera.edge import device_field, parse_edge_devices
from apps.camera.models import Camera
from apps.main.models import Hall
from toyxona.celery import app
from toyxona.redis import redis_delete, redis_expire, redis_getset, redis_set_nx

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")
CAMERA_INFO_KEY = "camera_task:{}"
HALL_SNAPSHOT_UPDATE_KEY = "hall_snapshot_update:{}"


def calc_countdown():
    now_t = timezone.now()
    if now_t.hour >= 15:
        countdown = int((now_t.replace(hour=6, minute=0, second=0, microsecond=0) + datetime.timedelta(
            days=1) - now_t).total_seconds())
    elif now_t.hour < 6:
        countdown = int((now_t.replace(hour=6, minute=0, second=0, microsecond=0) - now_t).total_seconds())
    else:
        countdown = 10 if settings.DEBUG else 600
    return countdown


def run_update_camera_info(camera_id):
    """Edge ga ROI yuborish — Celery bo'lmasa sinxron fallback."""
    try:
        res = update_camera_info.apply_async(kwargs={'camera_id': camera_id})
        key = CAMERA_INFO_KEY.format(camera_id)
        old_task_id = redis_getset(key, res.id)
        if old_task_id and old_task_id.decode() != res.id:
            app.control.revoke(old_task_id.decode(), terminate=True)
        redis_expire(key, 7 * 24 * 3600)
        return res
    except Exception as exc:
        print(f"run_update_camera_info async failed: {exc}")
        try:
            camera = Camera.objects.get(pk=camera_id)
            sync_camera_info(camera, timeout=15)
            return True
        except Exception as sync_exc:
            print(f"sync_camera_info fallback failed: {sync_exc}")
        return None


def sync_camera_info(camera, timeout=10):
    missing = []
    if not camera.device_sn:
        missing.append("device_sn")
    if not camera.hall_id:
        missing.append("hall")
    elif not camera.hall.server_ip:
        missing.append("hall.server_ip")
    if not (camera.username or "").strip():
        missing.append("username")
    if not (camera.password or "").strip():
        missing.append("password")
    if not ACCESS_TOKEN:
        missing.append("CONTROL_ACCESS_TOKEN")
    if missing:
        print(f"\tNo data: {', '.join(missing)}")
        return

    rois = camera.roi if isinstance(camera.roi, list) else []
    data = {
        camera.device_sn: {
            "ip": camera.camera_ip,
            "port": camera.camera_port,
            "username": camera.username,
            "password": camera.password,
            "stream_port": camera.camera_port,
            "rois": rois,
            "use_ai": camera.use_ai,
        }
    }
    url = f"http://{camera.hall.server_ip}:1984/api/update-devices"
    resp = requests.post(url, json=data, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}, timeout=timeout)
    print(f"\tpost {url} -> {resp.status_code}")


@app.task(bind=True, ignore_result=True, max_retries=None)
def update_camera_info(self, camera_id, started_at=None):
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    if started_at is None:
        started_at = now
    if now - started_at > 7 * 24 * 3600:
        return
    try:
        camera = Camera.objects.get(pk=camera_id)
        sync_camera_info(camera, timeout=15)
    except Camera.DoesNotExist:
        print("\tcamera not found")
    except Exception as e:
        raise self.retry(exc=e, countdown=calc_countdown(), kwargs={
            'camera_id': camera_id, 'started_at': started_at,
        })


def run_sync_cameras(hall_id, force_update=False):
    """Rasm yangilash: Celery yo'q bo'lsa sinxron ishlaydi (qotib qolmaslik uchun)."""
    import os

    key = HALL_SNAPSHOT_UPDATE_KEY.format(hall_id)
    use_celery = os.getenv("USE_CELERY_CAMERA_SYNC", "false").lower() == "true"

    if not use_celery:
        sync_cameras(
            hall_id,
            force_update=force_update,
            clear_redis_key=False,
            skip_snapshots=not force_update,
        )
        return True

    if not redis_set_nx(key, "-", ex=300):
        return False
    try:
        sync_cameras.apply_async(kwargs={
            "hall_id": hall_id,
            "force_update": force_update,
            "clear_redis_key": True,
        })
        return True
    except Exception as exc:
        print(f"sync_cameras async failed: {exc}")
        redis_delete(key)
        sync_cameras(
            hall_id,
            force_update=force_update,
            clear_redis_key=True,
            skip_snapshots=not force_update,
        )
        return True


@app.task(ignore_result=True, max_retries=None)
def sync_cameras(hall_id, force_update=False, clear_redis_key=False, skip_snapshots=False):
    def remove_key():
        if clear_redis_key:
            redis_delete(HALL_SNAPSHOT_UPDATE_KEY.format(hall_id))

    with ExitStack() as stack:
        stack.callback(remove_key)
        with transaction.atomic():
            try:
                hall = Hall.objects.select_for_update().get(pk=hall_id)
            except Exception as e:
                print(f"{hall_id}: {e}")
                return

            try:
                data = parse_edge_devices(
                    hall.server_ip,
                    ACCESS_TOKEN,
                    timeout=settings.EDGE_DEVICES_TIMEOUT,
                )
            except Exception as e:
                print("Error:", e)
                Camera.objects.filter(hall_id=hall.id).update(is_online=False)
                return

            if not data:
                print("\t0 devices from edge API")
                return

            Hall.objects.filter(pk=hall.id).update(is_online=True)
            print(f"\t{len(data)} devices from edge API")
            host = f"http://{hall.server_ip}:1984"

            camera_by_sn = {
                cam.device_sn: cam
                for cam in hall.camera_set.exclude(device_sn__isnull=True).exclude(device_sn="")
            }
            edge_sns = set()
            new_devices = []
            updated = 0
            n = Camera.objects.filter(hall_id=hall.id).count()

            for dev in data:
                sn = device_field(dev, "device_sn")
                if not sn:
                    continue
                edge_sns.add(sn)
                mac = device_field(dev, "mac", "unknown")
                ip = device_field(dev, "ip")

                cam = camera_by_sn.get(sn)
                if cam is None:
                    cam = Camera(
                        hall_id=hall.id,
                        device_sn=sn,
                        name=f"Camera {n + 1}",
                        camera_mac=mac,
                        camera_ip=ip,
                        username=device_field(dev, "username") or "",
                        password=device_field(dev, "password") or "",
                        is_active=True,
                        is_online=device_field(dev, "is_online", False),
                    )
                    new_devices.append(cam)
                    camera_by_sn[sn] = cam
                    n += 1
                    continue

                cam.device_sn = sn
                cam.camera_mac = mac
                if ip:
                    cam.camera_ip = ip
                cam.is_active = True
                cam.is_online = device_field(dev, "is_online", False)
                if device_field(dev, "username"):
                    cam.username = device_field(dev, "username")
                if device_field(dev, "password"):
                    cam.password = device_field(dev, "password")
                cam.save()
                updated += 1

            if new_devices:
                Camera.objects.bulk_create(new_devices, batch_size=50)

            stale = hall.camera_set.exclude(device_sn__in=edge_sns)
            stale_count = stale.count()
            if stale_count:
                stale.update(is_active=False, is_online=False)

            print(f"\tcreated={len(new_devices)} updated={updated} deactivated={stale_count}")
            camera_set = list(
                Camera.objects.filter(hall_id=hall.id, is_active=True).order_by("id")
            )
            update_cameras = {
                cam.device_sn: cam.id
                for cam in camera_set
                if cam.device_sn
            }

            for cam_id in update_cameras.values():
                run_update_camera_info(cam_id)

            if skip_snapshots:
                print("\tsnapshots skipped")
            else:
                for cam in camera_set:
                    save_screenshot(cam, f"{host}/api/snapshot/{cam.device_sn}", force_update)
                    cam.save()


def save_screenshot(cam, snapshot_url, force_update):
    if not cam.device_sn:
        return False
    try:
        upload_to = Camera._meta.get_field('screenshot').upload_to
        subpath = os.path.join(upload_to, str(cam.hall_id), str(cam.id) + ".jpg")
        file_path = os.path.join(settings.MEDIA_ROOT, str(subpath))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if not os.path.exists(file_path) or force_update:
            response = requests.get(
                snapshot_url,
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                timeout=settings.EDGE_API_TIMEOUT,
            )
            if response.status_code == 200:
                file_path_tmp = file_path + ".tmp"
                with open(file_path_tmp, 'wb') as f:
                    f.write(response.content)
                if os.path.getsize(file_path_tmp) > 1000:
                    os.rename(file_path_tmp, file_path)
                else:
                    os.remove(file_path_tmp)
                    subpath = None
            else:
                subpath = cam.screenshot.name

        if os.path.exists(file_path) and os.path.getsize(file_path) < 1000:
            os.remove(file_path)
            subpath = None

        cam.screenshot.name = subpath
        return True
    except Exception as e:
        print(f"\terror: {e}")
    return False
