"""Debug A5 overlapping issue."""
from m3s import A5Grid
import numpy as np

grid = A5Grid(9)  # High precision to see overlap issues

# Test nearby points that should have different cells
test_points = [
    (51.5074, -0.1278),    # London center
    (51.5074, -0.1279),    # Very close to London
    (51.5074, -0.1280),    # Slightly further
    (51.5075, -0.1278),    # Different latitude
    (51.5076, -0.1278),    # Further latitude
]

cells = []
for i, (lat, lon) in enumerate(test_points):
    cell = grid.get_cell_from_point(lat, lon)
    cells.append(cell)
    print(f"Point {i+1} ({lat}, {lon}):")
    print(f"  Cell ID: {cell.identifier}")
    print(f"  Cell bounds: {cell.polygon.bounds}")
    print(f"  Cell center: ({cell.polygon.centroid.y}, {cell.polygon.centroid.x})")
    print()

# Check for overlaps
print("Overlap analysis:")
for i in range(len(cells)):
    for j in range(i+1, len(cells)):
        overlap = cells[i].polygon.intersection(cells[j].polygon)
        overlap_area = overlap.area if hasattr(overlap, 'area') else 0
        if overlap_area > 0:
            print(f"Cells {i+1} and {j+1} overlap! Overlap area: {overlap_area}")
            print(f"  Cell {i+1} ID: {cells[i].identifier}")
            print(f"  Cell {j+1} ID: {cells[j].identifier}")
        else:
            print(f"Cells {i+1} and {j+1}: No overlap")

print()
print("Unique identifiers:")
identifiers = set(cell.identifier for cell in cells)
print(f"Total cells: {len(cells)}")
print(f"Unique cells: {len(identifiers)}")
if len(identifiers) < len(cells):
    print("PROBLEM: Some cells have identical identifiers!")