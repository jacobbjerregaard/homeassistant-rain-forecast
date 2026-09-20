"""Unit tests for the lifetime rainfall accumulator state machine.

Loaded directly from its file so these tests run without a Home Assistant
install, matching the approach in ``test_parser.py``.
"""

import importlib.util
import sys
from pathlib import Path

_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "rain_forecast"
    / "accumulator.py"
)
_spec = importlib.util.spec_from_file_location("rf_accumulator", _PATH)
_module = importlib.util.module_from_spec(_spec)
sys.modules["rf_accumulator"] = _module
_spec.loader.exec_module(_module)
RainAccumulator = _module.RainAccumulator

DAY1 = "2026-06-17"
DAY2 = "2026-06-18"


def test_first_sample_only_baselines():
    """The first sample must not be added, or a restart double counts."""
    acc = RainAccumulator()
    assert acc.add(5.0, DAY1) == 0.0


def test_rising_within_a_day_adds_the_delta():
    acc = RainAccumulator()
    acc.add(1.0, DAY1)
    assert acc.add(1.5, DAY1) == 0.5
    assert acc.add(2.0, DAY1) == 1.0


def test_downward_revision_never_rewinds_the_total():
    """The whole point of issue #1: the source figure can be revised down."""
    acc = RainAccumulator()
    acc.add(1.0, DAY1)
    acc.add(3.0, DAY1)  # total 2.0
    assert acc.add(2.0, DAY1) == 2.0  # revised down, total held
    # ...and the next rise is measured from the revised value, not the peak.
    assert acc.add(2.5, DAY1) == 2.5


def test_day_rollover_adds_the_new_day_in_full():
    acc = RainAccumulator()
    acc.add(1.0, DAY1)
    acc.add(4.0, DAY1)  # total 3.0
    assert acc.add(0.5, DAY2) == 3.5


def test_day_rollover_from_zero_adds_nothing():
    """Just after midnight the new day has no elapsed hours yet."""
    acc = RainAccumulator()
    acc.add(1.0, DAY1)
    acc.add(4.0, DAY1)  # total 3.0
    assert acc.add(0.0, DAY2) == 3.0


def test_restart_restores_the_total_and_rebaselines():
    acc = RainAccumulator()
    acc.add(1.0, DAY1)
    acc.add(4.0, DAY1)  # total 3.0

    restarted = RainAccumulator()
    restarted.reset_baseline(3.0)
    # Same day, rain already at 4.0: the restored total must not gain 4.0 again.
    assert restarted.add(4.0, DAY1) == 3.0
    assert restarted.add(4.5, DAY1) == 3.5


def test_unknown_value_is_ignored():
    acc = RainAccumulator()
    acc.add(1.0, DAY1)
    acc.add(2.0, DAY1)  # total 1.0
    assert acc.add(None, DAY1) == 1.0
    assert acc.add(2.5, DAY1) == 1.5


def test_unknown_date_still_accumulates():
    """A missing daily forecast must not stall the total forever."""
    acc = RainAccumulator()
    acc.add(1.0, None)
    assert acc.add(2.0, None) == 1.0
    assert acc.add(3.0, None) == 2.0
