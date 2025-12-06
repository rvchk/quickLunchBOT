from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from functools import wraps

_cache: Dict[str, tuple[Any, datetime]] = {}
_cache_ttl: Dict[str, timedelta] = {}

def cache_result(ttl_seconds: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            if cache_key in _cache:
                value, timestamp = _cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=ttl_seconds):
                    return value
            
            result = await func(*args, **kwargs)
            _cache[cache_key] = (result, datetime.now())
            return result
        
        return wrapper
    return decorator

def clear_cache(pattern: Optional[str] = None):
    if pattern is None:
        _cache.clear()
    else:
        keys_to_remove = [k for k in _cache.keys() if pattern in k]
        for key in keys_to_remove:
            _cache.pop(key, None)






