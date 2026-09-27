
import logging
import time
import functools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

_base_logger = logging.getLogger("resume_extractor")


class _PIIRedactingLogger:

    def _safe_mask(self, msg: str) -> str:
        try:
            from security import mask_pii
            return mask_pii(str(msg))
        except Exception:
            return str(msg)  

    def info(self, msg, *a, **kw):
        _base_logger.info(self._safe_mask(msg), *a, **kw)

    def warning(self, msg, *a, **kw):
        _base_logger.warning(self._safe_mask(msg), *a, **kw)

    def error(self, msg, *a, **kw):
        _base_logger.error(self._safe_mask(msg), *a, **kw)

    def debug(self, msg, *a, **kw):
        _base_logger.debug(self._safe_mask(msg), *a, **kw)


logger = _PIIRedactingLogger()


def log_call(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.time()
        logger.info(f"START {fn.__name__}")
        try:
            result = fn(*args, **kwargs)
            latency = time.time() - start
            logger.info(f"END {fn.__name__} | latency={latency:.2f}s")
            return result
        except Exception as e:
            latency = time.time() - start
            logger.error(f"FAILED {fn.__name__} | latency={latency:.2f}s | error={e}")
            raise
    return wrapper


def log_token_usage(response, label: str = "call"):
    usage = getattr(response, "usage", None)
    if usage:
        logger.info(f"TOKENS[{label}] input={usage.input_tokens} output={usage.output_tokens}")
