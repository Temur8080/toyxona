from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.account.forms import LoginForm


class AccountLoginView(LoginView):
    template_name = 'account/login.j2'
    form_class = LoginForm


class HallSuspendedView(LoginRequiredMixin, TemplateView):
    template_name = 'account/hall-suspended.j2'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_hall_activity_blocked():
            return redirect("counting:hall-choice")
        return super().dispatch(request, *args, **kwargs)
