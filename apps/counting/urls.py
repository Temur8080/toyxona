from django.urls import path

from apps.counting.views import CountingDashboardView, CountingHallChoiceView

app_name = 'counting'

urlpatterns = [
    path("", CountingHallChoiceView.as_view(), name="hall-choice"),
    path("<int:pk>/", CountingDashboardView.as_view(), name="dashboard"),
]
