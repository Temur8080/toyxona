from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].label = _("Login")
        self.fields['password'].label = _("Parol")

        field_class = "form-control login-input"
        self.fields['username'].widget.attrs.update({
            "class": field_class,
            "placeholder": _("Foydalanuvchi nomi"),
            "autocomplete": "username",
        })
        self.fields['password'].widget.attrs.update({
            "class": field_class,
            "placeholder": _("Parolingiz"),
            "autocomplete": "current-password",
        })

