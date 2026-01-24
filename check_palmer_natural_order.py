"""
Check Palmer's origins in NATURAL order (before Hilbert reordering).
"""

import math
from a5.core.dodecahedron_quaternions import quaternions
from a5.core.constants import interhedral_angle, PI_OVER_5, TWO_PI_OVER_5

# Recreate natural order generation
print("Natural order origin generation:")
print("="*80)

origins_natural = []

# North pole (natural 0)
print(f"0: North pole, quat_idx=0, quat={quaternions[0]}")
origins_natural.append((0, quaternions[0]))

# Middle band - interleaved rings
for i in range(5):
    alpha = i * TWO_PI_OVER_5
    alpha2 = alpha + PI_OVER_5

    # Ring 1 origin (natural 1, 3, 5, 7, 9)
    quat_idx_ring1 = i + 1
    natural_id_ring1 = 2*i + 1
    print(f"{natural_id_ring1}: Ring1 i={i}, alpha={alpha:.4f}, quat_idx={quat_idx_ring1}, quat={quaternions[quat_idx_ring1]}")
    origins_natural.append((natural_id_ring1, quaternions[quat_idx_ring1]))

    # Ring 2 origin (natural 2, 4, 6, 8, 10)
    quat_idx_ring2 = (i + 3) % 5 + 6
    natural_id_ring2 = 2*i + 2
    print(f"{natural_id_ring2}: Ring2 i={i}, alpha2={alpha2:.4f}, quat_idx={quat_idx_ring2}, quat={quaternions[quat_idx_ring2]}")
    origins_natural.append((natural_id_ring2, quaternions[quat_idx_ring2]))

# South pole (natural 11)
print(f"11: South pole, quat_idx=11, quat={quaternions[11]}")
origins_natural.append((11, quaternions[11]))

print("\nNatural order summary:")
for nat_id, quat in origins_natural:
    print(f"  Natural {nat_id}: quat={quat}")
