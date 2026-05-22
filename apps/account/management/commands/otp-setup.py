from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = "Superuser uchun OTP (Google Authenticator) qurilmasini yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("username", nargs="?", default=None)
        parser.add_argument("--name", default="phone")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        if not username:
            user = User.objects.filter(is_superuser=True).order_by("id").first()
            if not user:
                self.stderr.write("Superuser topilmadi. Username bering: python manage.py otp-setup admin")
                return
        else:
            user = User.objects.get(username=username)

        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])

        device, created = TOTPDevice.objects.get_or_create(
            user=user,
            name=options["name"],
            defaults={"confirmed": False},
        )
        if not created and device.confirmed:
            self.stdout.write(f"OTP allaqachon tasdiqlangan: {user.username} / {device.name} (id={device.id})")
            return

        device.confirmed = False
        device.save(update_fields=["confirmed"])

        self.stdout.write(self.style.SUCCESS(f"Foydalanuvchi: {user.username}"))
        self.stdout.write(f"OTP device id: {device.id}")
        self.stdout.write("")
        self.stdout.write("1) Google Authenticator yoki Authy oching")
        self.stdout.write("2) QR kod yoki qo'lda kalit qo'shing:")
        self.stdout.write(f"   {device.config_url}")
        self.stdout.write("")
        self.stdout.write("3) 6 xonali kodni oling va tasdiqlang:")
        self.stdout.write(f"   python manage.py otp-confirm {device.id} KOD")
        self.stdout.write("")
        self.stdout.write("Vaqtinchalik kod (test):")
        self.stdout.write(f"   python manage.py otp --id {device.id}")
