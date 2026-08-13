import time


def is_transient_gemini_error(exc):
    text = str(exc)
    code = getattr(exc, "status_code", None)
    if code in {429, 500, 503}:
        return True
    return any(
        token in text
        for token in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "high demand", "INTERNAL")
    )


def with_gemini_retry(fn, attempts=4, base_delay=3.0, label="Gemini"):
    """Retry transient Gemini 429/500/503 spikes."""
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
            if not is_transient_gemini_error(exc) or i == attempts - 1:
                raise
            delay = base_delay * (2 ** i)
            print(f"{label} busy ({exc}); retry {i + 1}/{attempts - 1} in {delay:.0f}s")
            time.sleep(delay)
    raise last
