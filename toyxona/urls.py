from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.utils.translation import gettext_lazy as _
from django.views.i18n import JavaScriptCatalog
from django_otp.admin import OTPAdminSite

urlpatterns = [
    path('control/', admin.site.urls),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += i18n_patterns(
    path("", include("apps.main.urls")),
    path("counting/", include("apps.counting.urls")),
    path("account/", include("apps.account.urls")),
    path("camera/", include("apps.camera.urls")),
    prefix_default_language=False,
)

admin.site.index_title = _('Toyxona')
admin.site.site_header = _('Toyxona boshqaruv')
admin.site.site_title = _('Toyxona')

if not settings.DEBUG and settings.OTP_ADMIN_REQUIRED:
    admin.site.__class__ = OTPAdminSite
