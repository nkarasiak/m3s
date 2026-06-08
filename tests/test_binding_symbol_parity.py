"""ADR 0001 P0 parity gate: the Python binding's public function set must match
the frozen contract (tests/golden/binding_symbols.json). The JS half asserts the
same contract in parity.cjs, so the two surfaces can never diverge.

The golden value tests (test_core_parity.py / parity.cjs) hand-list the ops they
check, so a new binding function can land on one side only and slip through. This
test pins the *full* public surface instead.

Run: ``uv run pytest tests/test_binding_symbol_parity.py``.
Regenerate the contract deliberately: ``uv run python tests/golden/generate.py``.
"""

import json
from pathlib import Path

import m3s_core

GOLDEN = Path(__file__).parent / "golden" / "binding_symbols.json"


def test_python_binding_matches_symbol_contract():
    expected = set(json.loads(GOLDEN.read_text()))
    actual = {
        name
        for name in dir(m3s_core)
        if not name.startswith("_") and callable(getattr(m3s_core, name))
    }
    assert actual == expected, (
        f"python binding surface drifted from the frozen contract\n"
        f"  added (regen golden if intended): {sorted(actual - expected)}\n"
        f"  removed:                          {sorted(expected - actual)}"
    )
