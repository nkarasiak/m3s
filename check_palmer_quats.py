from a5.core.dodecahedron_quaternions import quaternions
from a5.core.origin import origins, ORIGIN_ORDER

print("Palmer's quaternions (natural order):")
for i, q in enumerate(quaternions):
    print(f"  {i}: {q}")

print("\nORIGIN_ORDER:", ORIGIN_ORDER)

print("\nOrigins (after reordering):")
for i, origin in enumerate(origins):
    print(f"  Hilbert {i}: natural_id={origin.id}, quat={origin.quat}")
