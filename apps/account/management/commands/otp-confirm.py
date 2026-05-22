from django.core.management import BaseCommand
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = "OTP qurilmasini 6 xonali kod bilan tasdiqlaydi."

    def add_arguments(self, parser):
        parser.add_argument("device_id", type=int)
        parser.add_argument("token", type=str)

    def handle(self, *args, **options):
        device = TOTPDevice.objects.get(id=options["device_id"])
        totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)

        if not totp.verify(options["token"], tolerance=1):
            self.stderr.write(self.style.ERROR("Kod noto'g'ri yoki muddati o'tgan."))
            return

        device.confirmed = True
        device.save(update_fields=["confirmed"])
        self.stdout.write(self.style.SUCCESS(f"OTP tasdiqlandi: {device.user.username} ({device.name})"))
        self.stdout.write("Endi /control/ ga kirishingiz mumkin.")
