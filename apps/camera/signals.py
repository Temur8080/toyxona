import hashlib
import json

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.camera.models import Camera
from apps.camera.tasks import run_update_camera_info


@receiver(pre_save, sender=Camera)
def before_camera_saved(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_values = None
    else:
        try:
            old = Camera.objects.get(pk=instance.pk)
            instance._old_values = {f.name: getattr(old, f.name) for f in instance._meta.fields}
            instance._old_values["roi"] = hashlib.sha256(
                (json.dumps(old.roi, sort_keys=True) if old.roi else "").encode()
            ).hexdigest()
        except Camera.DoesNotExist:
            instance._old_values = None


@receiver(post_save, sender=Camera)
def after_camera_saved(sender, instance, created, **kwargs):
    if created:
        if (
            instance.device_sn
            and (instance.username or "").strip()
            and (instance.password or "").strip()
        ):
            run_update_camera_info(instance.pk)
        return

    fields = {"username", "password", "roi", "camera_port", "use_ai"}
    old_values = getattr(instance, "_old_values", None)
    if not old_values:
        return

    changed = {}
    for f in instance._meta.fields:
        field_name = f.name
        old = old_values.get(field_name)
        new = getattr(instance, field_name)
        if field_name == "roi":
            new = hashlib.sha256(
                (json.dumps(new, sort_keys=True) if new else "").encode()
            ).hexdigest()

        if old != new:
            changed[field_name] = True

    if "roi" in changed and instance.roi and isinstance(instance.roi, list) and len(instance.roi) > 0:
        if not instance.use_ai:
            Camera.objects.filter(pk=instance.pk).update(use_ai=True)
            instance.use_ai = True

    if fields & set(changed.keys()):
        run_update_camera_info(instance.pk)
