from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from apps.main.hall_status import refresh_allowed_halls


class HallChoiceView(LoginRequiredMixin, TemplateView):
    """Toyxona tanlash — kamera va counting uchun umumiy view."""
    template_name = 'main/hall-choice.j2'

    route_name = ""
    page_subtitle = ""
    show_online_status = True
    extra_builder = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["route"] = self.route_name
        context["PAGE_TITLE"] = _("Toyxonalar")
        context["PAGE_SUBTITLE"] = self.page_subtitle
        context["title"] = context["PAGE_TITLE"]
        if self.show_online_status:
            context["show_online"] = True
            context["ALLOWED_HALL"] = refresh_allowed_halls(self.request)
        if self.extra_builder:
            context["extra"] = self.extra_builder()
        return context
