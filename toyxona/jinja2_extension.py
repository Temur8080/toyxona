import os
from datetime import timedelta

from humanize import intcomma
from jinja2.ext import Extension

from toyxona.security import camera_signer


class ToyxonaUtils(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        environment.globals['env'] = self.env
        environment.globals['is_current'] = self.is_current
        environment.globals['is_active'] = self.is_active
        environment.filters['sec_to_hhmmss'] = self.sec_to_hhmmss
        environment.filters['sign'] = self.sign
        environment.filters['intcomma'] = self.intcomma
        environment.filters['datetime_format'] = self.datetime_format

    def sec_to_hhmmss(self, secs):
        return str(timedelta(seconds=int(secs)))

    def sign(self, val):
        return camera_signer.sign(val)

    def env(self, value, default=""):
        return os.getenv(value, default)

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
