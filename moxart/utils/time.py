from datetime import datetime, timezone


def utcnow():
    """Naive UTC timestamp, matching the timezone-less DATETIME columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
