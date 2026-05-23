from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.camera.models import Camera
from apps.main.models import Hall


class PeopleCount(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, verbose_name=_("Toyxona"))
    camera = models.ForeignKey(
        Camera, on_delete=models.SET_NULL, null=True, blank=True, default=None,
        verbose_name=_("Kamera"),
    )
    count = models.PositiveIntegerField(default=0, verbose_name=_("Odamlar soni"))
    recorded_at = models.DateTimeField(verbose_name=_("Vaqt"), db_index=True)

    class Meta:
        verbose_name = _("Odamlar soni")
        verbose_name_plural = _("Odamlar soni tarixi")
        ordering = ('-recorded_at',)
        indexes = [
            models.Index(fields=['hall', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.hall_id}: {self.count} ({self.recorded_at:%d.%m.%Y %H:%M})"

    @property
    def is_toy_level(self):
        from django.conf import settings
        return self.count >= int(getattr(settings, "TOY_EVENT_THRESHOLD", 12))


class HallEvent(models.Model):
    """Toyxona tadbir (toy) — odamlar soni threshold dan oshganda."""
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name="events", verbose_name=_("Toyxona"))
    started_at = models.DateTimeField(verbose_name=_("Boshlangan"))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tugagan"))
    peak_count = models.PositiveIntegerField(default=0, verbose_name=_("Eng ko'p odam"))
    is_active = models.BooleanField(default=True, verbose_name=_("Hozir davom etmoqda"))

    class Meta:
        verbose_name = _("Toy (tadbir)")
        verbose_name_plural = _("Toylar")
        ordering = ("-started_at",)
        indexes = [
            models.Index(fields=["hall", "is_active"]),
        ]

    def __str__(self):
        status = _("faol") if self.is_active else _("tugagan")
        return f"{self.hall_id}: {self.peak_count} ({status})"
