import logging


def setup_logger(name: str = "sonus"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        # in-memory ring buffer handler for debug posting
        class RingBufferHandler(logging.Handler):
            def __init__(self, capacity: int = 500):
                super().__init__()
                self.capacity = capacity
                self.buffer: list[str] = []

            def emit(self, record: logging.LogRecord) -> None:
                try:
                    msg = self.format(record)
                except Exception:
                    msg = f"{record.levelname}: {record.getMessage()}"
                self.buffer.append(msg)
                if len(self.buffer) > self.capacity:
                    self.buffer.pop(0)

            def recent(self, n: int = 200) -> list[str]:
                return self.buffer[-n:]

        ring = RingBufferHandler()
        ring.setFormatter(formatter)
        logger.addHandler(ring)
        logger.setLevel(logging.INFO)
        # expose recent accessor
        logger._ring_handler = ring
    return logger
