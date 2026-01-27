from m3s import precision


def test_best_precision_from_string_target():
    choice = precision.best("geohash", target="1km")
    assert isinstance(choice.precision, int)
    assert "size_m" in choice.metrics


def test_best_precision_area_target():
    choice = precision.best("geohash", target="2km2")
    assert isinstance(choice.precision, int)
    assert "area_km2" in choice.metrics
