import os

from django.core.signing import TimestampSigner

try:
    import pwd
except ImportError:
    pwd = None  # pwd is Unix-only; not available on Windows

camera_signer = TimestampSigner(salt='camera-websocket-token', sep=":@:")


def switch_to_www_data():
    if pwd is None:
        print("Cannot switch user: pwd module not available (Windows)")
        return
    try:
        user = pwd.getpwnam('www-data')
        os.setgid(user.pw_gid)
        os.setuid(user.pw_uid)
        print(f"Switched to {user.pw_name}:{user.pw_name}")
    except Exception as e:
        print(f"Cannot switch user: {e}")
