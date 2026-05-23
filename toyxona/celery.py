import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'toyxona.settings')

app = Celery('toyxona')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.timezone = settings.TIME_ZONE
app.conf.enable_utc = False
app.conf.broker_connection_retry_on_startup = True

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

interval = getattr(settings, "PEOPLE_COUNT_SYNC_INTERVAL", 300)
if settings.CELERY_BROKER_URL:
    app.conf.beat_schedule = {
        "sync-people-count": {
            "task": "apps.counting.tasks.sync_people_count_all_halls",
            "schedule": float(interval),
        },
    }
