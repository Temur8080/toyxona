import json
import os
from urllib.parse import parse_qs, urlparse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.camera.models import Camera
from apps.camera.serializers import CameraRoiSerializer
from apps.camera.tasks import HALL_SNAPSHOT_UPDATE_KEY, run_sync_cameras
from apps.main.hall_status import refresh_allowed_halls
from apps.main.models import Hall
from toyxona.helpers import to_int
from toyxona.redis import redis_delete, redis_exists, redis_ttl
from toyxona.security import camera_signer


class CameraHallChoiceView(LoginRequiredMixin, TemplateView):
    template_name = 'main/hall-choice.j2'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["route"] = "camera:list"
        context["PAGE_TITLE"] = _("Toyxonalar")
        context["PAGE_SUBTITLE"] = _("Kamera ro'yxati uchun toyxonani tanlang")
        context["title"] = context["PAGE_TITLE"]
        context["show_online"] = True
        context["ALLOWED_HALL"] = refresh_allowed_halls(self.request)
        context["extra"] = {
            hid: _("{0}/{1} ta kamera").format(m, n)
            for hid, n, m in Camera.objects.filter(is_active=True).values("hall_id").annotate(
                n=Count("id"), m=Count("id", filter=Q(is_online=True)),
            ).values_list("hall_id", "n", "m")
        }
        return context


class CameraListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Camera
    paginate_by = 24
    ordering = ('id',)
    permission_required = "camera.view_camera"
    template_name = 'camera/list.j2'

    def get(self, request, *args, **kwargs):
        self.set_hall(request, *args, **kwargs)

        if request.GET.get('load') == 'true' and request.user.has_perm('camera.change_camera'):
            from apps.camera.tasks import sync_cameras
            try:
                sync_cameras(self.hall.id, force_update=False, skip_snapshots=True)
                messages.success(request, _("Kameralar edge serverdan yuklandi"))
            except Exception as exc:
                messages.error(request, _("Kameralarni yuklashda xato: {0}").format(exc))
            return redirect('camera:list', self.hall.id)

        if request.GET.get('activate_all') == 'true' and request.user.has_perm('camera.change_camera'):
            n = Camera.objects.filter(hall_id=self.hall.id, is_active=False).update(is_active=True)
            messages.success(request, _("{0} ta kamera faollashtirildi").format(n))
            return redirect('camera:list', self.hall.id)

        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset().filter(hall_id=self.hall.id)
        if self.request.GET.get('show_all') != 'true':
            qs = qs.filter(is_active=True)
        return qs.order_by("id")

    def render_to_response(self, context, **response_kwargs):
        if self.request.user.has_perm("camera.change_camera"):
            u_ok = self.request.GET.get("u", "false") == "true"
            o_ok = self.request.GET.get("o", "false") == "true"
            remove_ok = to_int(self.request.GET.get("r", 0), 0)

            if u_ok or o_ok:
                if run_sync_cameras(self.hall.id, force_update=u_ok):
                    messages.success(self.request, _("Rasmlarni yangilanish boshlandi"))
                else:
                    messages.warning(self.request, _("Rasmlar yangilanish jarayonida..."))
                return redirect("camera:list", self.hall.id)
            if self.request.GET.get("check", "false") == "true":
                return HttpResponse(str(self.get_updating()).lower())
            if remove_ok > 0:
                try:
                    cam = Camera.objects.get(id=remove_ok, hall_id=self.hall.id)
                    if cam.screenshot:
                        cam.screenshot.delete()
                        cam.screenshot = None
                        cam.save()
                        messages.success(self.request, _("Screenshot o'chirildi"))
                except Camera.DoesNotExist:
                    pass
        return super().render_to_response(context, **response_kwargs)

    def set_hall(self, request, *args, **kwargs):
        try:
            self.hall = Hall.objects.filter(
                id__in=request.user.allowed_hall.values_list('id', flat=True)
            ).get(pk=kwargs['pk'])
        except Hall.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["hall"] = self.hall
        context["PAGE_TITLE"] = str(self.hall)
        context["PAGE_SUBTITLE"] = _("Kamera snapshot va live stream")
        context["updating"] = self.get_updating()
        hall_id = self.hall.id
        context["camera_counts"] = {
            "active": Camera.objects.filter(hall_id=hall_id, is_active=True).count(),
            "inactive": Camera.objects.filter(hall_id=hall_id, is_active=False).count(),
            "total": Camera.objects.filter(hall_id=hall_id).count(),
        }
        context["show_all"] = self.request.GET.get("show_all") == "true"
        return context

    def get_updating(self):
        key = HALL_SNAPSHOT_UPDATE_KEY.format(self.hall.id)
        if not redis_exists(key):
            return False
        ttl = redis_ttl(key)
        # Celery ishlamasa qulf 5 daqiqadan keyin o'zi tugaydi; -1 = eski qulf
        if ttl in (-1, -2):
            redis_delete(key)
            return False
        return True


class CameraPreview(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    TITLE = _("Kamerani ko'rish")
    model = Camera
    template_name = 'camera/preview.j2'
    permission_required = "camera.view_camera"

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] = str(self.object.hall)
        context["PAGE_SUBTITLE"] = self.object.name
        context["stream_host"] = os.getenv("CAMERA_STREAM_HOST")
        return context


class CameraVerifyView(View):
    def get(self, request, *args, **kwargs):
        try:
            parsed = urlparse(request.META.get("HTTP_X_ORIGINAL_URI", ""))
            token = parse_qs(parsed.query).get('token', [None])[0]
            if not token:
                raise ValueError("token missing")
            hall_id, device_sn = camera_signer.unsign(token, max_age=30).split(":", 1)
            hall = Hall.objects.get(id=hall_id)
            resp = HttpResponse("OK")
            resp["X-Device-SN"] = device_sn
            resp["X-Server-IP"] = hall.server_ip
            return resp
        except Exception:
            if settings.DEBUG:
                raise
            return HttpResponseForbidden()


class CameraAiPreview(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    TITLE = _("AI ko'rinish")
    model = Camera
    template_name = 'camera/preview-ai.j2'
    permission_required = "camera.view_camera"

    def _edge_headers(self):
        return {"Authorization": f"Bearer {os.environ.get('CONTROL_ACCESS_TOKEN')}"}

    def _edge_get(self, camera, path, timeout=10):
        if not camera.hall.server_ip:
            raise ValueError("server_ip missing")
        url = f"http://{camera.hall.server_ip}:1984{path}"
        return requests.get(url, headers=self._edge_headers(), timeout=timeout)

    def render_to_response(self, context, **response_kwargs):
        camera = self.object
        image_mode = self.request.GET.get("image", "false").lower() == "true"
        data_mode = self.request.GET.get("data", "false").lower() == "true"

        if image_mode:
            for path in (
                f"/api/ai/snapshot/{camera.device_sn}",
                f"/api/snapshot/{camera.device_sn}",
            ):
                try:
                    response = self._edge_get(camera, path)
                    response.raise_for_status()
                    return HttpResponse(
                        response.content,
                        content_type=response.headers.get("Content-Type", "image/jpeg"),
                    )
                except Exception:
                    continue
            return HttpResponse(status=404)

        if data_mode:
            for path in (
                f"/api/ai/poses/{camera.device_sn}",
                f"/api/ai/skeleton/{camera.device_sn}",
                f"/api/ai/keypoints/{camera.device_sn}",
            ):
                try:
                    response = self._edge_get(camera, path)
                    if response.status_code == 200:
                        return HttpResponse(
                            response.content,
                            content_type=response.headers.get("Content-Type", "application/json"),
                        )
                except Exception:
                    continue
            return HttpResponse(json.dumps({"persons": []}), content_type="application/json")

        return super().render_to_response(context, **response_kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] = str(self.object.hall)
        context["PAGE_SUBTITLE"] = f"{self.object.name} · {_('AI skeleton')}"
        context["preview_url"] = self.request.path
        context["live_preview_url"] = reverse('camera:preview', args=[self.object.pk])
        return context


class CameraRoiEditView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Camera
    permission_required = "camera.change_camera"
    template_name = 'camera/roi.j2'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError as e:
            return HttpResponse(json.dumps({"success": False, "message": str(e)}), content_type="application/json")

        ser = CameraRoiSerializer(data=payload, many=True)
        if not ser.is_valid():
            return HttpResponse(json.dumps({
                "success": False, "message": "Invalid data", "errors": ser.errors,
            }), content_type="application/json")

        self.object.roi = ser.validated_data
        self.object.save()
        return HttpResponse(json.dumps({"success": True, "message": str(_("Saqlandi"))}), content_type="application/json")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] = str(self.object.hall)
        context["PAGE_SUBTITLE"] = f"{self.object.name} · ROI"
        return context

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
