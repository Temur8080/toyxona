import os

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from apps.camera.models import Camera
from apps.counting.models import PeopleCount
from apps.main.models import Hall


class CountingHallChoiceView(LoginRequiredMixin, TemplateView):
    template_name = 'main/hall-choice.j2'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["route"] = "counting:dashboard"
        context["PAGE_TITLE"] = _("Toyxonalar")
        context["PAGE_SUBTITLE"] = _("Odamlar soni monitoringi uchun toyxonani tanlang")
        context["title"] = context["PAGE_TITLE"]
        context["extra"] = {
            hid: _("{0} ta kamera").format(n)
            for hid, n in Camera.objects.filter(is_active=True).values("hall_id").annotate(
                n=Count("id"),
            ).values_list("hall_id", "n")
        }
        return context


class CountingDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'counting/dashboard.j2'
    permission_required = "counting.view_peoplecount"

    def get(self, request, *args, **kwargs):
        self.hall = self.get_hall(request, kwargs)
        return super().get(request, *args, **kwargs)

    def get_hall(self, request, kwargs):
        return Hall.objects.filter(
            id__in=request.user.allowed_hall.values_list('id', flat=True)
        ).get(pk=kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hall = self.hall
        context["hall"] = hall
        context["PAGE_TITLE"] = str(hall)
        context["PAGE_SUBTITLE"] = _("Odamlar soni va bugungi dinamika")

        latest = PeopleCount.objects.filter(hall_id=hall.id).order_by('-recorded_at').first()
        context["current_count"] = latest.count if latest else 0
        context["current_time"] = timezone.localtime(latest.recorded_at) if latest else None
        context["max_capacity"] = hall.max_capacity
        context["fill_percent"] = (
            round(latest.count / hall.max_capacity * 100, 1)
            if latest and hall.max_capacity else None
        )

        today = timezone.localtime().date()
        history = list(PeopleCount.objects.filter(
            hall_id=hall.id,
            recorded_at__date=today,
        ).order_by('-recorded_at')[:50])
        context["history"] = history

        chart_rows = list(reversed(history[-12:]))
        max_count = max((row.count for row in chart_rows), default=0) or 1
        context["chart_points"] = [{
            "count": row.count,
            "time": timezone.localtime(row.recorded_at).strftime("%H:%M"),
            "height": max(8, int(row.count / max_count * 100)),
        } for row in chart_rows]

        return context
