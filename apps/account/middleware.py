from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import Resolver404, resolve, reverse


class HallActivitySuspendedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if not user.is_authenticated or not user.is_hall_activity_blocked():
            return self.get_response(request)

        path = request.path
        if user.is_staff and path.startswith("/control/"):
            return self.get_response(request)
        if path.startswith(settings.STATIC_URL) or path.startswith(settings.MEDIA_URL):
            return self.get_response(request)
        if settings.DEBUG and path.startswith("/__debug__/"):
            return self.get_response(request)

        try:
            match = resolve(path)
        except Resolver404:
            return self.get_response(request)

        if match.namespace == "account" and match.url_name in {"login", "logout", "hall_suspended"}:
            return self.get_response(request)

        target = reverse("account:hall_suspended")
        if path.rstrip("/") == target.rstrip("/"):
            return self.get_response(request)

        return HttpResponseRedirect(target)
