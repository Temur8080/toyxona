from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.main.models import Hall


class User(AbstractUser):
    allowed_hall = models.ManyToManyField(Hall, verbose_name=_("Ruxsat berilgan toyxonalar"), blank=True)

    def is_hall_activity_blocked(self):
        if not self.is_active or self.is_superuser:
            return False
        ids = list(self.allowed_hall.values_list("pk", flat=True))
        if len(ids) != 1:
            return False
        try:
            hall = Hall.objects.only("activity_suspended").get(pk=ids[0])
        except Hall.DoesNotExist:
            return False
        return bool(hall.activity_suspended)
