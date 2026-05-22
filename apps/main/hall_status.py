from apps.main.models import Hall


def refresh_allowed_halls(request, *, save=True, check_files_count=False):
    """Foydalanuvchi toyxonalari uchun ping va (ixtiyoriy) DB yangilash."""
    hall_ids = list(request.user.allowed_hall.values_list("id", flat=True))
    if not hall_ids:
        return []
    Hall.check_online(
        update=save,
        check_files_count=check_files_count,
        hall_ids=hall_ids,
    )
    return list(
        request.user.allowed_hall.prefetch_related("district__region").order_by("id")
    )
