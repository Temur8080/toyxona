from django.contrib.auth.views import LogoutView
from django.urls import path

from apps.account.views import AccountLoginView, HallSuspendedView

app_name = 'account'
urlpatterns = [
    path("login/", AccountLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("hall-suspended/", HallSuspendedView.as_view(), name="hall_suspended"),
]
