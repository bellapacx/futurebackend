import functools
import logging
from functools import lru_cache

import httpx
from supabase import Client, create_client

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_service_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_secret_key)


def with_db_retry(func):
    """
    Retry once on transient PostgREST connection errors.

    httpx 0.28 (used by supabase-py 2.33) can raise `ReadError: [Errno 11]
    Resource temporarily unavailable` when the HTTP/2 keep-alive connection
    to Supabase has gone stale. A single retry reopens the socket and
    succeeds ~100% of the time. See httpx/httpcore#2758.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except httpx.ReadError as exc:
            logger.warning("PostgREST ReadError, retrying once: %s", exc)
            return func(*args, **kwargs)
        except httpx.ConnectError as exc:
            logger.warning("PostgREST ConnectError, retrying once: %s", exc)
            return func(*args, **kwargs)

    return wrapper