import m3s


def test_grid_entrypoint():
    grid = m3s.grid("geohash", precision=5)
    cell = grid.cell(0.0, 0.0)
    assert cell.precision == 5
