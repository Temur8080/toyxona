import os
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from django.db import models
from django.utils.translation import gettext_lazy as _

from toyxona.translation import i18n

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")


def _ping_host(ip):
    if not ip:
        return False
    try:
        if platform.system().lower() == 'windows':
            cmd = ['ping', '-n', '1', '-w', '1000', ip]
        else:
            cmd = ['ping', '-c', '1', '-W', '1', ip]
        ret = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ret.returncode == 0
    except OSError:
        return False


def _fetch_app_version(ip):
    if not ip:
        return '-'
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    try:
        info_data = requests.get(
            f"http://{ip}:1984/api/info",
            headers=headers,
            timeout=5,
        ).json()
        version = info_data.get('version') or info_data.get('app_version')
        if version:
            return str(version)[:50]
    except Exception:
        pass
    try:
        resp = requests.get(f"http://{ip}:1984/api/version", headers=headers, timeout=5)
        if resp.status_code == 200 and resp.text.strip():
            return resp.text.strip()[:50]
    except Exception:
        pass
    return '-'


@i18n
class Region(models.Model):
    name_uz = models.CharField(max_length=100, verbose_name=_("Viloyat nomi"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Viloyat")
        verbose_name_plural = _("Viloyatlar")


@i18n
class District(models.Model):
    region = models.ForeignKey(Region, on_delete=models.RESTRICT)
    name_uz = models.CharField(max_length=100, verbose_name=_("Tuman nomi"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Tuman")
        verbose_name_plural = _("Tumanlar")


@i18n
class Hall(models.Model):
    district = models.ForeignKey(District, on_delete=models.RESTRICT, verbose_name=_("Joylashgan tuman"))
    name_uz = models.CharField(max_length=100, verbose_name=_("Toyxona nomi"))
    slug = models.CharField(max_length=30, unique=True, verbose_name=_("Slug"))
    server_user = models.CharField(max_length=50, null=True, blank=True, default=None)
    server_ip = models.GenericIPAddressField(null=True, blank=True, default=None)
    server_port = models.PositiveSmallIntegerField(default=22)
    is_online = models.BooleanField(default=False, verbose_name=_("Online"), editable=False)
    app_version = models.CharField(max_length=50, default='-', editable=False)
    max_capacity = models.PositiveIntegerField(default=0, verbose_name=_("Maksimal sig'im"))
    activity_suspended = models.BooleanField(default=False, verbose_name=_("Faoliyati to'xtatilgan"))

    @classmethod
    def ping(cls, hall_id, ip, check_files_count=False):
        is_online = _ping_host(ip)
        files_count, cameras_count, states_count, app_version = 0, 0, -1, '-'

        if ip and check_files_count:
            try:
                info_data = requests.get(
                    f"http://{ip}:1984/api/info",
                    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                    timeout=5,
                ).json()
                files_count = info_data.get("files_count", 0)
                cameras_count = info_data.get("cameras_count", 0)
                states_count = info_data.get("states_count", -1)
                is_online = True
            except Exception:
                pass
            app_version = _fetch_app_version(ip)

        return hall_id, is_online, files_count, cameras_count, states_count, app_version

    @classmethod
    def check_online(cls, update=False, *, check_files_count=False, hall_ids=None):
        qs = Hall.objects.order_by("id")
        if hall_ids is not None:
            qs = qs.filter(id__in=hall_ids)
        halls = list(qs.all())
        max_workers = min(50, len(halls) or 1)
        result_by_id = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(cls.ping, hall.id, hall.server_ip, check_files_count)
                for hall in halls
            ]
            for future in as_completed(futures):
                hall_id, is_online, files_count, cameras_count, states_count, app_version = future.result()
                result_by_id[hall_id] = (is_online, files_count, cameras_count, states_count, app_version)

        result = []
        for hall in halls:
            hall.is_online, hall.files_count, hall.cameras_count, hall.states_count, hall.app_version = result_by_id[hall.id]
            if update:
                hall.save(update_fields=["is_online"])
            result.append(hall)

        return result

    def __str__(self):
        if hasattr(self, "display_name"):
            return self.display_name
        return self.name

    class Meta:
        verbose_name = _("Toyxona")
        verbose_name_plural = _("Toyxonalar")
        permissions = (
            ("hall_online", "Toyxona server holati"),
        )
