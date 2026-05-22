def toyxona(request):
    if not request.user.is_authenticated:
        return {}

    current_title = ""
    cls = request.resolver_match.func
    if cls and hasattr(cls, "view_class"):
        cls = cls.view_class
        if cls and hasattr(cls, "TITLE"):
            current_title = cls.TITLE

    allowed_hall = list(
        request.user.allowed_hall.prefetch_related('district__region').order_by("id").all()
    )
    return {
        "ALLOWED_HALL": allowed_hall,
        "ALLOWED_HALL_ID": {row.id for row in allowed_hall},
        "TITLE": current_title,
    }
