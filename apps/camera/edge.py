import requests
from rest_framework.exceptions import ValidationError

from apps.camera.serializers import DeviceInfo


def _extract_device_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("devices", "data", "items", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def fetch_devices_payload(host, token, timeout=15):
    """Edge :1984 dan kamera ro'yxatini oladi."""
    headers = {"Authorization": f"Bearer {token}"}
    for path in ("/api/devices", "/api/discovery"):
        try:
            resp = requests.get(
                f"http://{host}:1984{path}",
                headers=headers,
                timeout=timeout,
            )
            resp.raise_for_status()
            rows = _extract_device_list(resp.json())
            if rows:
                return rows
        except Exception:
            continue
    return []


def normalize_edge_device(raw):
    if not isinstance(raw, dict):
        return None
    sn = (raw.get("device_sn") or raw.get("sn") or "").strip()
    if not sn:
        return None

    mac = (raw.get("mac") or raw.get("camera_mac") or "").strip()
    if mac:
        mac = mac.replace(":", "-").lower()

    ip = (
        raw.get("ip_v4_address")
        or raw.get("ip")
        or raw.get("camera_ip")
        or ""
    )
    if isinstance(ip, str):
        ip = ip.strip()

    return {
        "device_sn": sn,
        "mac": mac or "unknown",
        "ip_v4_address": ip or "0.0.0.0",
        "is_online": bool(raw.get("is_online", True)),
        "username": (raw.get("username") or "").strip(),
        "password": (raw.get("password") or "").strip(),
    }


def parse_edge_devices(host, token, timeout=15):
    rows = []
    for raw in fetch_devices_payload(host, token, timeout=timeout):
        item = normalize_edge_device(raw)
        if item:
            rows.append(item)

    if not rows:
        return []

    serializer = DeviceInfo(data=rows, many=True)
    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as exc:
        raise ValueError(f"DeviceInfo: {exc.detail}") from exc
    return serializer.validated_data
