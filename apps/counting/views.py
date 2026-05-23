from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from apps.camera.models import Camera
from apps.counting.models import PeopleCount
from apps.counting.services import sync_people_count_for_hall
from apps.main.hall_choice import HallChoiceView
from apps.main.models import Hall
from toyxona.redis import redis_set_nx

PEOPLE_SYNC_INTERVAL_SEC = 60


def _counting_hall_extra():
    return {
        hid: _("{0} ta kamera").format(n)
        for hid, n in Camera.objects.filter(is_active=True).values("hall_id").annotate(
            n=Count("id"),
        ).values_list("hall_id", "n")
    }


class CountingHallChoiceView(HallChoiceView):
    route_name = "counting:dashboard"
    page_subtitle = _("Odamlar soni monitoringi uchun toyxonani tanlang")
    extra_builder = _counting_hall_extra


def _dashboard_context(hall):
    latest = PeopleCount.objects.filter(hall_id=hall.id).order_by("-recorded_at").first()
    today = timezone.localtime().date()
    history = list(PeopleCount.objects.filter(
        hall_id=hall.id,
        recorded_at__date=today,
    ).order_by("-recorded_at")[:50])
    chart_rows = list(reversed(history[-12:]))
    max_count = max((row.count for row in chart_rows), default=0) or 1
    ai_cameras = Camera.objects.filter(hall_id=hall.id, is_active=True, use_ai=True).count()
    roi_cameras = Camera.objects.filter(
        hall_id=hall.id, is_active=True, use_ai=True,
    ).exclude(Q(roi__isnull=True) | Q(roi=[])).count()

    return {
        "hall": hall,
        "PAGE_TITLE": str(hall),
        "PAGE_SUBTITLE": _("Odamlar soni va bugungi dinamika"),
        "current_count": latest.count if latest else 0,
        "current_time": timezone.localtime(latest.recorded_at) if latest else None,
        "max_capacity": hall.max_capacity,
        "fill_percent": (
            round(latest.count / hall.max_capacity * 100, 1)
            if latest and hall.max_capacity else None
        ),
        "history": history,
        "chart_points": [{
            "count": row.count,
            "time": timezone.localtime(row.recorded_at).strftime("%H:%M"),
            "height": max(8, int(row.count / max_count * 100)),
        } for row in chart_rows],
        "ai_cameras": ai_cameras,
        "roi_cameras": roi_cameras,
    }


class CountingDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "counting/dashboard.j2"
    permission_required = "counting.view_peoplecount"

    def get(self, request, *args, **kwargs):
        self.hall = self.get_hall(request, kwargs)

        if request.GET.get("sync") == "1":
            result = sync_people_count_for_hall(self.hall.id, force=True)
            if request.GET.get("format") == "json":
                return JsonResponse(result, safe=False)
            if result.get("saved"):
                messages.success(request, _("Yangilandi: {0} kishi").format(result.get("count", 0)))
            elif result.get("ok"):
                messages.info(request, _("Ma'lumot o'zgarmagan: {0} kishi").format(result.get("count", 0)))
            else:
                err = result.get("error", "unknown")
                messages.warning(request, _("Edge dan olinmadi ({0})").format(err))
            return redirect("counting:dashboard", self.hall.pk)

        if request.GET.get("format") == "json":
            ctx = _dashboard_context(self.hall)
            return JsonResponse({
                "current_count": ctx["current_count"],
                "current_time": (
                    ctx["current_time"].strftime("%d.%m.%Y %H:%M")
                    if ctx["current_time"] else None
                ),
                "fill_percent": ctx["fill_percent"],
            })

        self._last_sync = None
        cache_key = f"people_sync:{self.hall.id}"
        if redis_set_nx(cache_key, "1", ex=PEOPLE_SYNC_INTERVAL_SEC):
            self._last_sync = sync_people_count_for_hall(self.hall.id)

        return super().get(request, *args, **kwargs)

    def get_hall(self, request, kwargs):
        return Hall.objects.filter(
            id__in=request.user.allowed_hall.values_list("id", flat=True),
        ).get(pk=kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_dashboard_context(self.hall))
        context["sync_result"] = getattr(self, "_last_sync", None)
        return context
