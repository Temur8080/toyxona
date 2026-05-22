import logging
import os

import redis

logger = logging.getLogger(__name__)

REDIS_CLIENT = redis.Redis(connection_pool=redis.ConnectionPool(
    host=os.environ.get('REDIS_HOST', '127.0.0.1'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=int(os.environ.get('REDIS_DB', 0)),
    socket_connect_timeout=1,
))


def _redis_call(default, func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except redis.RedisError as exc:
        logger.warning('Redis unavailable: %s', exc)
        return default


def redis_exists(key):
    return bool(_redis_call(0, REDIS_CLIENT.exists, key))


def redis_set_nx(key, value, ex=None):
    return _redis_call(True, REDIS_CLIENT.set, key, value, nx=True, ex=ex)


def redis_getset(key, value):
    return _redis_call(None, REDIS_CLIENT.getset, key, value)


def redis_expire(key, seconds):
    _redis_call(None, REDIS_CLIENT.expire, key, seconds)


def redis_delete(key):
    _redis_call(None, REDIS_CLIENT.delete, key)


def redis_ttl(key):
    return _redis_call(-2, REDIS_CLIENT.ttl, key)
