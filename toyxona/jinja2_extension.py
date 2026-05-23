from humanize import intcomma
from jinja2.ext import Extension

from toyxona.security import camera_stream_token


class ToyxonaUtils(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        environment.globals['is_current'] = self.is_current
        environment.globals['is_active'] = self.is_active
        environment.filters['sign'] = self.sign
        environment.filters['intcomma'] = self.intcomma
        environment.filters['datetime_format'] = self.datetime_format

    def sign(self, val):
        if "|" in str(val):
            hall_id, device_sn = str(val).split("|", 1)
            return camera_stream_token(hall_id, device_sn)
        return camera_stream_token(val, "")

    def is_current(self, request, routes, extra_cond=None):
        routes_set = set(routes.split(","))
        vv = request.resolver_match.view_name in routes_set
        return vv and extra_cond if extra_cond is not None else vv

    def is_active(self, request, routes, cls="active", extra_cond=None):
        return cls if self.is_current(request, routes, extra_cond) else ""

    def intcomma(self, value):
        return str(intcomma(value)).replace(",", " ")

    def datetime_format(self, value):
        return f"{value:%d.%m.%Y %H:%M}"
