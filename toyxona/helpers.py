def to_int(s, default=None):
    try:
        return int(s)
    except (ValueError, TypeError):
        return default
