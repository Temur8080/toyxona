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
