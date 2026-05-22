from django.urls import path, re_path
from django.views.generic import RedirectView

from apps.main.views import (
    MainDashboardView,
    MainHallData,
    MainHallOnline,
    MainHallRunSnapshot,
    MainHallSmartControl,
    MainHallTestDiscovery,
    MainHallTestSsh,
    MainIndexView,
)

app_name = 'main'

urlpatterns = [
    path("", MainIndexView.as_view(), name="index"),
    path("dashboard/", MainDashboardView.as_view(), name="dashboard"),
    path("hall/online/", MainHallOnline.as_view(), name="hall-online"),
    path("bazaar/online/", RedirectView.as_view(pattern_name="main:hall-online", permanent=False)),
    path("hall/test-ssh/<int:pk>/", MainHallTestSsh.as_view(), name="hall-test-ssh"),
    path("hall/test-sbc/<int:pk>/", MainHallSmartControl.as_view(), name="hall-test-sbc"),
    path("hall/test-discovery/<int:pk>/", MainHallTestDiscovery.as_view(), name="hall-test-discovery"),
    path("hall/test-run-snapshot/<int:pk>/", MainHallRunSnapshot.as_view(), name="hall-test-run-snapshot"),
    re_path(r"hall/(?P<pk>\d+)/data/(?P<path>.*)", MainHallData.as_view(), name="hall-data"),
]
