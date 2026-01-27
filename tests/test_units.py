from m3s.units import parse_area, parse_length


def test_parse_length_units():
    assert parse_length("1km") == 1000.0
    assert parse_length("250m") == 250.0
    assert parse_length("1000ft") == 304.8
    assert parse_length("1mile") == 1609.344


def test_parse_area_units():
    assert parse_area("1km2") == 1.0
    assert parse_area("1000000m2") == 1.0
    assert parse_area("1mi2") == 2.589988110336
