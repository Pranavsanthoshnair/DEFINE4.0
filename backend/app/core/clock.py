"""
Clock interface and implementations for Veylo.

Allows deterministic simulation and time acceleration during testing
and demo runs (H14, H19) without blocking real-time execution.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Protocol


class Clock(Protocol):
    """Abstract clock interface providing the current UTC timestamp."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""
        ...


class SystemClock:
    """Standard system clock returning actual real-world UTC time."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class SimClock:
    """Controllable simulated clock for fast deterministic testing and simulation."""

    def __init__(self, initial_time: datetime | None = None) -> None:
        self._current_time = initial_time or datetime(2026, 10, 10, 9, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._current_time

    def set_time(self, new_time: datetime) -> None:
        """Set the simulated clock to a specific timestamp."""
        if new_time.tzinfo is None:
            new_time = new_time.replace(tzinfo=timezone.utc)
        self._current_time = new_time

    def advance(self, delta: timedelta) -> datetime:
        """Advance the simulated clock by the given timedelta."""
        self._current_time += delta
        return self._current_time

    def advance_seconds(self, seconds: float) -> datetime:
        """Advance the simulated clock by a number of seconds."""
        return self.advance(timedelta(seconds=seconds))

    def advance_minutes(self, minutes: float) -> datetime:
        """Advance the simulated clock by a number of minutes."""
        return self.advance(timedelta(minutes=minutes))

    def advance_hours(self, hours: float) -> datetime:
        """Advance the simulated clock by a number of hours."""
        return self.advance(timedelta(hours=hours))


_system_clock = SystemClock()
_sim_clock = SimClock()


def get_clock(simulated: bool = False) -> Clock:
    """Get the active clock instance."""
    return _sim_clock if simulated else _system_clock
