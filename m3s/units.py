"""Unit parsing helpers for precision targets."""

from __future__ import annotations

import re

_LENGTH_UNITS = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "metre": 1.0,
    "metres": 1.0,
    "km": 1000.0,
    "kilometer": 1000.0,
    "kilometers": 1000.0,
    "kilometre": 1000.0,
    "kilometres": 1000.0,
    "ft": 0.3048,
    "foot": 0.3048,
    "feet": 0.3048,
    "mi": 1609.344,
    "mile": 1609.344,
    "miles": 1609.344,
}

_AREA_UNITS = {
    "m2": 1.0 / 1_000_000.0,
    "m^2": 1.0 / 1_000_000.0,
    "sqm": 1.0 / 1_000_000.0,
    "sq m": 1.0 / 1_000_000.0,
    "sq meter": 1.0 / 1_000_000.0,
    "sq meters": 1.0 / 1_000_000.0,
    "square meter": 1.0 / 1_000_000.0,
    "square meters": 1.0 / 1_000_000.0,
    "km2": 1.0,
    "km^2": 1.0,
    "sqkm": 1.0,
    "sq km": 1.0,
    "sq kilometer": 1.0,
    "sq kilometers": 1.0,
    "square kilometer": 1.0,
    "square kilometers": 1.0,
    "mi2": 2.589988110336,
    "mi^2": 2.589988110336,
    "sqmi": 2.589988110336,
    "sq mi": 2.589988110336,
    "sq mile": 2.589988110336,
    "sq miles": 2.589988110336,
    "square mile": 2.589988110336,
    "square miles": 2.589988110336,
}

_NUMBER_UNIT_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*([a-zA-Z \^0-9]+)\s*$")


def parse_length(value: str) -> float:
    """Parse a length string into meters."""
    match = _NUMBER_UNIT_RE.match(value)
    if not match:
        raise ValueError(f"Invalid length value: {value!r}")
    number_str, unit_str = match.groups()
    unit = unit_str.strip().lower()
    if unit not in _LENGTH_UNITS:
        raise ValueError(f"Unknown length unit: {unit_str!r}")
    return float(number_str) * _LENGTH_UNITS[unit]


def parse_area(value: str) -> float:
    """Parse an area string into square kilometers."""
    match = _NUMBER_UNIT_RE.match(value)
    if not match:
        raise ValueError(f"Invalid area value: {value!r}")
    number_str, unit_str = match.groups()
    unit = unit_str.strip().lower()
    if unit not in _AREA_UNITS:
        raise ValueError(f"Unknown area unit: {unit_str!r}")
    return float(number_str) * _AREA_UNITS[unit]


def detect_area(value: str) -> bool:
    """Return True if the string looks like an area value."""
    text = value.strip().lower()
    return any(
        token in text
        for token in (
            "km2",
            "km^2",
            "m2",
            "m^2",
            "sq ",
            "sqkm",
            "sqm",
            "square",
            "mi2",
            "mi^2",
            "sqmi",
        )
    )
