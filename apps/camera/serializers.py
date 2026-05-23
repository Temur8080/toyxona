import re
import uuid

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.camera.models import Camera

ZONE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,29}$")


def normalize_zone_value(raw):
    """Zona nomini edge uchun: faqat kichik harf, raqam, _, -"""
    value = (raw or "").strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_-")
    if value and ZONE_PATTERN.match(value):
        return value
    return f"zona_{uuid.uuid4().hex[:8]}"


class CameraRoiPointSerializer(serializers.Serializer):
    x = serializers.IntegerField()
    y = serializers.IntegerField()


class CameraRoiSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=36)
    type = serializers.IntegerField(required=False, default=Camera.TYPE_ZONE)
    value = serializers.CharField(required=False, allow_blank=True, default="")
    points = CameraRoiPointSerializer(many=True)

    def validate_id(self, value):
        value = str(value).strip() if value is not None else ""
        if not value:
            return str(uuid.uuid4())
        try:
            uuid.UUID(value)
            return value
        except ValueError:
            slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_-").lower()
            if slug and len(slug) <= 36:
                return slug
            return str(uuid.uuid4())

    def validate(self, attrs):
        attrs["value"] = normalize_zone_value(attrs.get("value"))
        points = attrs.get("points") or []
        if len(points) < 3:
            raise ValidationError({"points": _("Zona kamida 3 ta nuqtadan iborat bo'lishi kerak")})
        if len(points) > 12:
            raise ValidationError({"points": _("Juda ko'p nuqta (max 12)")})
        return attrs


class DeviceInfo(serializers.Serializer):
    device_sn = serializers.CharField(required=True)
    mac = serializers.CharField(required=False, allow_blank=True, default="unknown")
    ip = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    is_online = serializers.BooleanField(required=False, default=False)
    username = serializers.CharField(required=False, allow_blank=True, default="")
    password = serializers.CharField(required=False, allow_blank=True, default="")
