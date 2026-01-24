"""
Debug all global coverage test points.
"""
import sys
sys.path.insert(0, '/tmp/a5-py')
import a5 as palmer_a5

from m3s import lonlat_to_cell

test_coords = [
    (0.0, 0.0),  # Equator/Prime Meridian
    (90.0, 45.0),  # Mid-latitude
    (-90.0, -45.0),  # Southern hemisphere
    (179.0, 85.0),  # Near north pole, dateline
    (-179.0, -85.0),  # Near south pole, dateline
    (139.6503, 35.6762),  # Tokyo
    (-58.3816, -34.6037),  # Buenos Aires
    (151.2093, -33.8688),  # Sydney
]

print("Global Coverage Test Results:")
print("="*80)

passing = 0
failing = 0

for lon, lat in test_coords:
    our_cell_id = lonlat_to_cell(lon, lat, 1)
    palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 1)

    match = "PASS" if our_cell_id == palmer_cell_id else "FAIL"
    if match == "PASS":
        passing += 1
    else:
        failing += 1

    print(f"{match} | ({lon:8.4f}, {lat:7.4f}) | Ours: 0x{our_cell_id:016x} | Palmer: 0x{palmer_cell_id:016x}")

print("="*80)
print(f"Results: {passing}/{len(test_coords)} passing, {failing}/{len(test_coords)} failing")
