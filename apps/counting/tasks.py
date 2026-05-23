from apps.counting.services import sync_all_halls
from toyxona.celery import app


@app.task(ignore_result=True)
def sync_people_count_all_halls():
    """Barcha toyxonalar uchun avtomatik odam sanash (Celery Beat)."""
    for hall, saved, count, msg in sync_all_halls():
        print(f"[sync-people] {hall}: {msg} count={count} saved={saved}")
