# extensions.py
import os
from flask import request

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:  # pragma: no cover - exercised only in dependency-limited envs
    class Limiter:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def init_app(self, app) -> None:
            return None

        def limit(self, *_args, **_kwargs):
            def decorator(fn):
                return fn
            return decorator

    def get_remote_address() -> str:
        return request.remote_addr or "127.0.0.1"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300 per day", "60 per hour"],
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URL", "memory://"),
)