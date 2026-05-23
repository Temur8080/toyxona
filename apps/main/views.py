import os
import subprocess

import requests
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_jinja.views.generic import DetailView

from apps.camera.edge import parse_edge_devices
from apps.camera.models import Camera
from apps.counting.models import HallEvent, PeopleCount
from apps.counting.services import toy_event_threshold
from apps.main.models import Hall

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")


class MainIndexView(TemplateView):
    template_name = 'main/index.j2'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('main:dashboard')
        return super().get(request, *args, **kwargs)


class MainDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard.j2'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hall_ids = list(self.request.user.allowed_hall.values_list('id', flat=True))
        if hall_ids:
            Hall.check_online(update=True, check_files_count=False, hall_ids=hall_ids)

        latest_subq = PeopleCount.objects.filter(
            hall_id=OuterRef('pk'),
        ).order_by('-recorded_at')

        halls = list(
            Hall.objects.filter(id__in=hall_ids)
            .select_related('district__region')
            .annotate(
                latest_count=Subquery(latest_subq.values('count')[:1]),
                latest_at=Subquery(latest_subq.values('recorded_at')[:1]),
            )
            .order_by('id')
        )

        camera_stats = Camera.objects.filter(hall_id__in=hall_ids, is_active=True).aggregate(
            total=Count('id'),
            online=Count('id', filter=Q(is_online=True)),
        )

        threshold = toy_event_threshold()
        active_events = {
            e.hall_id: e
            for e in HallEvent.objects.filter(hall_id__in=hall_ids, is_active=True)
        }

        for hall in halls:
            if hall.latest_count and hall.max_capacity:
                hall.fill_percent = round(hall.latest_count / hall.max_capacity * 100, 1)
            else:
                hall.fill_percent = None
            hall.active_toy = active_events.get(hall.id)
            hall.is_toy_now = bool(hall.active_toy) or (
                hall.latest_count is not None and hall.latest_count >= threshold
            )

        context.update({
            'PAGE_TITLE': _('Dashboard'),
            'PAGE_SUBTITLE': _('Toyxonalar va odamlar soni bo\'yicha umumiy ko\'rinish'),
            'halls': halls,
            'total_people': sum(h.latest_count or 0 for h in halls),
            'halls_online': sum(1 for h in halls if h.is_online),
            'halls_total': len(halls),
            'camera_stats': camera_stats,
            'recent_activity': PeopleCount.objects.filter(
                hall_id__in=hall_ids,
            ).select_related('hall', 'camera').order_by('-recorded_at')[:12],
            'today_records': PeopleCount.objects.filter(
                hall_id__in=hall_ids,
                recorded_at__date=timezone.localdate(),
            ).count(),
            'active_toys_count': len(active_events),
            'toy_threshold': threshold,
        })
        return context


class MainHallOnline(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'main/hall-online.j2'
    permission_required = "main.hall_online"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] = _('Server holati')
        context["PAGE_SUBTITLE"] = _('Edge serverlar, kameralar va AI holati')
        context["result"] = Hall.check_online(True, check_files_count=True)
        return context


class MainHallTestSsh(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Hall
    template_name = 'main/test-ssh.j2'
    permission_required = "main.hall_online"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        success, result, return_code, msg = self.check_ssh_and_get_time()
        context.update({
            "PAGE_TITLE": str(self.object),
            "PAGE_SUBTITLE": _("SSH test"),
            "success": success,
            "result": result,
            "return_code": return_code,
            "msg": msg,
        })
        return context

    def check_ssh_and_get_time(self):
        cmd = self._ssh_cmd()
        timeout = 15
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, None, -1, f"timeout after {timeout}s"
        except FileNotFoundError as exc:
            return False, None, -1, f"ssh binary not found: {exc}"
        except Exception as exc:
            return False, None, -1, f"unexpected error: {exc}"

        stdout = proc.stdout.decode(errors='ignore').strip()
        stderr = proc.stderr.decode(errors='ignore').strip()

        if proc.returncode == 0 and stdout:
            first_line = stdout.splitlines()[0].strip()
            return True, first_line, proc.returncode, stderr or "ok"

        msg = stderr or stdout or f"ssh exited with code {proc.returncode}"
        return False, None, proc.returncode, msg

    def _ssh_cmd(self):
        identity = str(settings.BASE_DIR / '.ssh' / 'id_ed25519')
        known_hosts = str(settings.BASE_DIR / '.ssh' / 'known_hosts')
        cmd = [
            "ssh",
            "-i", identity,
            "-p", str(self.object.server_port),
            "-o", "BatchMode=yes",
            "-o", "ExitOnForwardFailure=yes",
            "-o", f"UserKnownHostsFile={known_hosts}",
            "-o", "StrictHostKeyChecking=accept-new",
            f"{self.object.server_user}@{self.object.server_ip}",
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-Date).ToString('o')",
        ]
        return cmd


class MainHallSmartControl(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Hall
    template_name = 'main/test-sbc.j2'
    permission_required = "main.hall_online"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] = str(self.object)
        context["PAGE_SUBTITLE"] = _("Edge server test (SBC)")

        try:
            context["version"] = requests.get(
                f"http://{self.object.server_ip}:1984/api/version",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                timeout=5,
            ).text
        except Exception as exc:
            context["version"] = str(exc)

        try:
            context["files_count"] = requests.get(
                f"http://{self.object.server_ip}:1984/api/snapshot/files/count",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                timeout=5,
            ).text
        except Exception as exc:
            context["files_count"] = str(exc)

        try:
            context["result"] = parse_edge_devices(self.object.server_ip, ACCESS_TOKEN, timeout=15)
        except Exception as exc:
            context["error"] = str(exc)

        return context


class MainHallData(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Hall
    permission_required = "main.hall_online"

    def render_to_response(self, context, **response_kwargs):
        try:
            resp = requests.get(
                f"http://{self.object.server_ip}:1984/snapshot/data/{self.kwargs['path']}",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                timeout=10,
            )
            resp.raise_for_status()
            return HttpResponse(resp.content, content_type=resp.headers['content-type'])
        except Exception as exc:
            return HttpResponse(str(exc))


class MainHallTestDiscovery(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Hall
    template_name = 'main/test-discovery.j2'
    permission_required = "main.hall_online"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] = str(self.object)
        context["PAGE_SUBTITLE"] = _("SADP discovery")

        try:
            req = requests.get(
                f"http://{self.object.server_ip}:1984/api/discovery",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                timeout=15,
            )
            if req.status_code == 200:
                context["result"] = req.text
            else:
                context["error"] = req.text
        except Exception as exc:
            context["error"] = str(exc)

        return context


class MainHallRunSnapshot(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Hall
    template_name = 'main/test-run-snapshot.j2'
    permission_required = "main.hall_online"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] = str(self.object)
        context["PAGE_SUBTITLE"] = _("Snapshot ishga tushirish")

        try:
            req = requests.get(
                f"http://{self.object.server_ip}:1984/api/run-snapshot",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                timeout=10,
            )
            context["result"] = req.json()
        except Exception as exc:
            context["error"] = str(exc)

        return context
