import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.camera.models import Camera


class CameraRoiPointSerializer(serializers.Serializer):
    x = serializers.IntegerField()
    y = serializers.IntegerField()


class CameraRoiSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.IntegerField(required=False, default=Camera.TYPE_ZONE)
    value = serializers.CharField(min_length=1, required=True)
    points = CameraRoiPointSerializer(many=True)

    ZONE_PATTERN = r"^[a-z0-9_-]+$"

    def validate(self, attrs):
        if not re.match(self.ZONE_PATTERN, attrs.get("value", "")):
            raise ValidationError({"value": _("Zona nomi noto'g'ri (masalan: zal, kirish)")})
        if len(attrs.get("points", [])) != 4:
            raise ValidationError({"points": _("Zona 4 ta nuqtadan iborat bo'lishi kerak")})
        return attrs


class DeviceInfo(serializers.Serializer):
    device_sn = serializers.CharField(required=True)
    mac = serializers.CharField(required=True)
    ip = serializers.CharField(required=True, source='ip_v4_address')
    is_online = serializers.BooleanField(required=False, default=False)
