import threading
import time
from collections import defaultdict, deque

# Thread-safe in-memory store for rate limiting
_lock = threading.Lock()

# user_id -> deque of accepted request timestamps (rolling window)
_accepted_timestamps: dict[str, deque] = defaultdict(deque)

# user_id -> count of rejected requests (cumulative)
_rejected_counts: dict[str, int] = defaultdict(int)

WINDOW_SECONDS = 60
MAX_REQUESTS = 5


def _clean_old_timestamps(user_id: str, now: float):
    """Remove timestamps older than the rolling window."""
    dq = _accepted_timestamps[user_id]
    while dq and now - dq[0] > WINDOW_SECONDS:
        dq.popleft()


def try_accept(user_id: str) -> bool:
    """
    Try to accept a request for user_id.
    Returns True if accepted, False if rate limited.
    Thread-safe.
    """
    now = time.time()
    with _lock:
        _clean_old_timestamps(user_id, now)
        count = len(_accepted_timestamps[user_id])
        if count < MAX_REQUESTS:
            _accepted_timestamps[user_id].append(now)
            return True
        else:
            _rejected_counts[user_id] += 1
            return False


def get_stats() -> dict:
    """Return per-user stats."""
    now = time.time()
    with _lock:
        all_users = set(_accepted_timestamps.keys()) | set(_rejected_counts.keys())
        result = {}
        for uid in all_users:
            _clean_old_timestamps(uid, now)
            result[uid] = {
                "user_id": uid,
                "accepted_current_window": len(_accepted_timestamps[uid]),
                "rejected_cumulative": _rejected_counts[uid],
            }
        return result