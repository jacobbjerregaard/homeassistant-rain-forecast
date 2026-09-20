"""Pure running-total logic for the lifetime rainfall sensor.

Like :mod:`parser`, this deliberately avoids any Home Assistant imports so the
state machine can be unit-tested without an HA install.
"""

from __future__ import annotations


class RainAccumulator:
    """A monotonic running total fed by a daily "rain so far today" figure.

    ``today_so_far`` restarts at zero every local midnight and, because it is
    re-derived from a model that revises hours already elapsed, can also fall
    *within* a day. Only upward movement is folded in, so a downward revision
    never rewinds the lifetime total.
    """

    def __init__(self, total: float = 0.0) -> None:
        """Start from ``total``, awaiting a baseline sample."""
        self.total = total
        self._baselined = False
        self._last_date: str | None = None
        self._last_value: float = 0.0

    def reset_baseline(self, total: float | None = None) -> None:
        """Forget the last sample so the next one only establishes a baseline.

        Called after a restart, where the restored total already accounts for
        everything recorded before the restart.
        """
        if total is not None:
            self.total = total
        self._baselined = False
        self._last_date = None
        self._last_value = 0.0

    def add(self, today_so_far: float | None, date: str | None) -> float:
        """Fold one coordinator sample into the total and return the new total.

        ``date`` identifies the local day ``today_so_far`` belongs to; it is
        only ever compared with the previous sample's, so an unknown day
        (``None``) degrades to "same day as last time" rather than stalling.
        """
        if today_so_far is None:
            return self.total

        if not self._baselined:
            # First sample after start/restart: baseline only, no addition, so a
            # mid-day restart cannot double count what is already in the total.
            self._baselined = True
        elif date == self._last_date:
            delta = today_so_far - self._last_value
            if delta > 0:
                self.total += delta
        else:
            # New day: the previous day's tail since our last poll is lost, but
            # today's accumulation so far is added in full.
            self.total += max(0.0, today_so_far)

        self._last_date = date
        self._last_value = today_so_far
        return self.total
