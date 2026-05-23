"""Edge server (:1984) HTTP proxy yordamchilari."""
import os

import requests
from django.conf import settings

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN", "")
MIN_FRAME_BYTES = 200


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
    try:
        return requests.get(url, headers=edge_headers(), timeout=timeout)
    except Exception:
        return None


def _valid_image_response(resp):
    if not resp or resp.status_code != 200:
        return False
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if ctype and "json" in ctype:
        return False
    return len(resp.content) >= MIN_FRAME_BYTES


def fetch_snapshot_bytes(camera, timeout=None):
    """Kamera snapshot — edge API (bir nechta yo'l)."""
    if not camera.device_sn or not camera.hall.server_ip:
        return None, None
    sn = camera.device_sn
    timeout = timeout or min(30, settings.EDGE_API_TIMEOUT)
    paths = (
        f"/api/ai/snapshot/{sn}",
        f"/api/snapshot/{sn}",
        f"/api/frame.jpeg?src={sn}",
        f"/api/frame.jpg?src={sn}",
    )
    for path in paths:
        resp = edge_get(camera.hall.server_ip, path, timeout=timeout)
        if _valid_image_response(resp):
            return resp.content, resp.headers.get("Content-Type", "image/jpeg")
    return None, None


def _read_saved_screenshot(camera):
    if not camera.screenshot:
        return None, None
    try:
        with camera.screenshot.open("rb") as fh:
            data = fh.read()
        if len(data) >= MIN_FRAME_BYTES:
            return data, "image/jpeg"
    except Exception:
        pass
    return None, None


def fetch_camera_frame_bytes(camera, timeout=None):
    """Edge snapshot; ishlamasa — saqlangan screenshot (502 oldini oladi)."""
    content, ctype = fetch_snapshot_bytes(camera, timeout=timeout)
    if content:
        return content, ctype, "edge"
    content, ctype = _read_saved_screenshot(camera)
    if content:
        return content, ctype, "cache"
    return None, None, None
