from apps.main.models import Hall
from toyxona.redis import redis_set_nx

HALL_PING_CACHE_SEC = 90


def refresh_allowed_halls(request, *, save=True, check_files_count=False):
    """Foydalanuvchi toyxonalari — ping 90s da bir marta (server qotmasin)."""
    hall_ids = list(request.user.allowed_hall.values_list("id", flat=True))
    if not hall_ids:
        return []

    cache_key = "hall_ping:{}:{}".format(
        request.user.id,
        ",".join(str(i) for i in sorted(hall_ids)),
    )
    if redis_set_nx(cache_key, "1", ex=HALL_PING_CACHE_SEC):
        Hall.check_online(
            update=save,
            check_files_count=check_files_count,
            hall_ids=hall_ids,
        )

    return list(
        request.user.allowed_hall.prefetch_related("district__region").order_by("id")
    )
