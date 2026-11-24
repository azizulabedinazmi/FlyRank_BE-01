"""Stretch: Redis is in the stack now (W4 jobs/caching will use it). For this week the app only pings it."""
import os

import redis


def redis_status() -> str:
    """'ok', 'down', or 'not configured'. Redis being down never breaks the task API."""
    url = os.environ.get("REDIS_URL")
    if not url:
        return "not configured"
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        return "ok" if client.ping() else "down"
    except redis.RedisError:
        return "down"
