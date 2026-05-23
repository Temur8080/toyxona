import json
import os
from urllib.parse import parse_qs, unquote, urlparse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView

from apps.camera.edge_proxy import ACCESS_TOKEN, fetch_snapshot_bytes
from apps.camera.models import Camera
from apps.camera.serializers import CameraRoiSerializer
from apps.camera.tasks import HALL_SNAPSHOT_UPDATE_KEY, run_sync_cameras, save_screenshot
from apps.main.hall_choice import HallChoiceView
from apps.main.models import Hall
from toyxona.helpers import to_int
from toyxona.redis import redis_delete, redis_exists, redis_ttl
from toyxona.security import camera_signer


def _camera_hall_extra():
    return {
        hid: _("{0}/{1} ta kamera").format(m, n)
        for hid, n, m in Camera.objects.filter(is_active=True).values("hall_id").annotate(
            n=Count("id"), m=Count("id", filter=Q(is_online=True)),
        ).values_list("hall_id", "n", "m")
    }


class CameraHallChoiceView(HallChoiceView):
    route_name = "camera:list"
    page_subtitle = _("Kamera ro'yxati uchun toyxonani tanlang")
    extra_builder = _camera_hall_extra


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
            from apps.camera.edge import parse_edge_devices

            try:
                before = Camera.objects.filter(hall_id=self.hall.id, is_active=True).count()
                sync_cameras(self.hall.id, force_update=False, skip_snapshots=True, push_edge=False)
                edge_n = len(parse_edge_devices(
                    self.hall.server_ip,
                    os.environ.get("CONTROL_ACCESS_TOKEN"),
                ))
                after = Camera.objects.filter(hall_id=self.hall.id, is_active=True).count()
                messages.success(request, _(
                    "Edge: {0} ta qurilma. Faol kameralar: {1} → {2}"
                ).format(edge_n, before, after))
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
        context["live_frame_url"] = reverse("camera-live-frame", args=[self.object.pk])
        return context


class CameraLiveFrameView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Live fallback — edge dan bitta JPEG kadr (til prefiksisiz URL)."""
    permission_required = "camera.view_camera"

    def get(self, request, pk, *args, **kwargs):
        camera = get_object_or_404(Camera.objects.filter(is_active=True), pk=pk)
        content, ctype = fetch_snapshot_bytes(camera, timeout=20)
        if content:
            resp = HttpResponse(content, content_type=ctype)
            resp["Cache-Control"] = "no-store"
            return resp
        return HttpResponse(status=502)


class CameraVerifyView(View):
    def get(self, request, *args, **kwargs):
        try:
            token = request.GET.get("token")
            if not token:
                parsed = urlparse(request.META.get("HTTP_X_ORIGINAL_URI", ""))
                token = parse_qs(parsed.query).get("token", [None])[0]
            if not token:
                raise ValueError("token missing")
            token = unquote(token)

            payload = camera_signer.unsign(token, max_age=3600)
            if "|" in payload:
                hall_id, device_sn = payload.split("|", 1)
            else:
                hall_id, device_sn = payload.split(":", 1)

            hall = Hall.objects.get(id=int(hall_id))
            if not hall.server_ip:
                raise ValueError("hall server_ip missing")
            if not device_sn:
                raise ValueError("device_sn missing")

            resp = HttpResponse("OK")
            resp["X-Device-SN"] = device_sn
            resp["X-Server-IP"] = hall.server_ip
            if ACCESS_TOKEN:
                resp["X-Edge-Authorization"] = f"Bearer {ACCESS_TOKEN}"
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
            return None
        url = f"http://{camera.hall.server_ip}:1984{path}"
        return requests.get(url, headers=self._edge_headers(), timeout=timeout)

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def render_to_response(self, context, **response_kwargs):
        camera = self.object
        preview_timeout = min(20, settings.EDGE_API_TIMEOUT)

        if self.request.GET.get("image", "").lower() == "true":
            sn = camera.device_sn
            for path in (
                f"/api/ai/snapshot/{sn}",
                f"/api/ai/snapshot/{sn}?overlay=1",
                f"/api/ai/snapshot/{sn}?draw=1",
                f"/api/snapshot/{sn}",
            ):
                try:
                    resp = self._edge_get(camera, path, timeout=preview_timeout)
                    if resp and resp.status_code == 200 and len(resp.content) > 500:
                        return HttpResponse(
                            resp.content,
                            content_type=resp.headers.get("Content-Type", "image/jpeg"),
                        )
                except Exception:
                    continue
            return HttpResponse(status=404)

        if self.request.GET.get("data", "").lower() == "true":
            sn = camera.device_sn
            for path in (
                f"/api/ai/poses/{sn}",
                f"/api/ai/skeleton/{sn}",
                f"/api/ai/keypoints/{sn}",
                f"/api/ai/pose/{sn}",
                f"/api/ai/detections/{sn}",
            ):
                try:
                    resp = self._edge_get(camera, path, timeout=preview_timeout)
                    if resp and resp.status_code == 200:
                        return HttpResponse(
                            resp.content,
                            content_type=resp.headers.get("Content-Type", "application/json"),
                        )
                except Exception:
                    continue
            return HttpResponse(
                json.dumps({"persons": []}),
                content_type="application/json",
            )

        return super().render_to_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] = str(self.object.hall)
        context["PAGE_SUBTITLE"] = f"{self.object.name} · {_('AI skeleton')}"
        context["preview_url"] = self.request.path
        context["live_preview_url"] = reverse("camera:preview", args=[self.object.pk])
        return context


class CameraRoiEditView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    TITLE = _("ROI (sanash zonasi)")
    model = Camera
    template_name = 'camera/roi.j2'
    permission_required = "camera.change_camera"

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.GET.get("frame") == "1":
            content, ctype = fetch_snapshot_bytes(self.object, timeout=60)
            if content:
                return HttpResponse(content, content_type=ctype)
            return HttpResponse(status=404)
        if request.GET.get("save_frame") == "1":
            host = f"http://{self.object.hall.server_ip}:1984"
            if self.object.device_sn and save_screenshot(
                self.object,
                f"{host}/api/snapshot/{self.object.device_sn}",
                force_update=True,
            ):
                self.object.save(update_fields=["screenshot"])
                messages.success(request, _("Snapshot saqlandi"))
            else:
                messages.error(request, _("Snapshot olinmadi (edge yoki token)"))
            return redirect("camera:roi", self.object.pk)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from rest_framework.exceptions import ValidationError as DRFValidationError

        self.object = self.get_object()
        try:
            data = json.loads(request.body)
            if not isinstance(data, list):
                raise ValueError(_("JSON ro'yxat bo'lishi kerak"))
            serializer = CameraRoiSerializer(data=data, many=True)
            serializer.is_valid(raise_exception=True)
            self.object.roi = serializer.validated_data
            self.object.save(update_fields=["roi"])
            from apps.camera.tasks import run_update_camera_info
            edge_synced = run_update_camera_info(self.object.id) is not None
            return HttpResponse(json.dumps({
                "ok": True,
                "message": str(_("ROI saqlandi")),
                "edge_synced": edge_synced,
            }), content_type="application/json")
        except DRFValidationError as exc:
            return HttpResponse(
                json.dumps({"ok": False, "errors": exc.detail}),
                status=400,
                content_type="application/json",
            )
        except json.JSONDecodeError:
            return HttpResponse(
                json.dumps({"ok": False, "error": _("JSON noto'g'ri")}),
                status=400,
                content_type="application/json",
            )
        except Exception as exc:
            if settings.DEBUG:
                raise
            return HttpResponse(
                json.dumps({"ok": False, "error": str(exc)}),
                status=400,
                content_type="application/json",
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] = str(self.object.hall)
        context["PAGE_SUBTITLE"] = self.object.name
        context["roi_json"] = json.dumps(self.object.roi or [])
        context["frame_url"] = f"{self.request.path}?frame=1"
        context["has_saved_screenshot"] = bool(self.object.screenshot)
        return context
