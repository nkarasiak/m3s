import pytest

from m3s import GeohashGrid
from m3s.relationships import RelationshipType, analyze_relationship, is_adjacent


def test_relationships_basic():
    grid = GeohashGrid(precision=4)
    cell1 = grid.cell(40.7128, -74.0060)
    cell2 = grid.cell(40.7138, -74.0060)

    rel = analyze_relationship(cell1, cell2)
    assert isinstance(rel, RelationshipType)

    adj = is_adjacent(cell1, cell2)
    assert isinstance(adj, bool)
