"""Edge server (:1984) HTTP proxy yordamchilari."""
import os

import requests
from django.conf import settings

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN", "")


def edge_headers():
    headers = {}
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    return headers


def edge_base_url(server_ip):
    return f"http://{server_ip}:1984"


def edge_get(server_ip, path, timeout=None):
    if not server_ip:
        return None
    timeout = timeout or settings.EDGE_API_TIMEOUT
    url = f"{edge_base_url(server_ip)}{path}"
    return requests.get(url, headers=edge_headers(), timeout=timeout)


def fetch_snapshot_bytes(camera, timeout=None):
    """Kamera snapshot (AI yoki oddiy)."""
    if not camera.device_sn or not camera.hall.server_ip:
        return None, None
    sn = camera.device_sn
    timeout = timeout or min(30, settings.EDGE_API_TIMEOUT)
    for path in (
        f"/api/ai/snapshot/{sn}",
        f"/api/snapshot/{sn}",
    ):
        try:
            resp = edge_get(camera.hall.server_ip, path, timeout=timeout)
            if resp and resp.status_code == 200 and len(resp.content) > 500:
                return resp.content, resp.headers.get("Content-Type", "image/jpeg")
        except Exception:
            continue
    return None, None
