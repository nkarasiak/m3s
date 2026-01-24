"""
Debug QUINTANT_FIRST reordering.
"""

import a5 as palmer_a5
from a5.core.origin import origins as palmer_origins, QUINTANT_FIRST as palmer_quintant_first

from m3s.a5.constants import QUINTANT_FIRST, _QUINTANT_FIRST_NATURAL, _ORIGIN_ORDER

print("="*80)
print("QUINTANT_FIRST Comparison")
print("="*80)

print("\nOur _ORIGIN_ORDER:", _ORIGIN_ORDER)

print("\nNatural order QUINTANT_FIRST (before reordering):")
print("  Ours:", _QUINTANT_FIRST_NATURAL)

print("\nReordered QUINTANT_FIRST (after Hilbert placement):")
print("  Ours:  ", QUINTANT_FIRST)
print("  Palmer:", palmer_quintant_first)
print("  Match: ", QUINTANT_FIRST == palmer_quintant_first)

print("\nPer-origin comparison:")
for i in range(12):
    our_val = QUINTANT_FIRST[i]
    palmer_val = palmer_quintant_first[i]
    palmer_origin = palmer_origins[i]
    match = "✓" if our_val == palmer_val else "✗"
    print(f"  Origin {i}: ours={our_val}, Palmer={palmer_val} {match}")
    if our_val != palmer_val:
        # Find what natural index this should be
        old_id = _ORIGIN_ORDER[i]
        print(f"    (Hilbert position {i} maps to natural position {old_id})")
        print(f"    Natural QUINTANT_FIRST[{old_id}] = {_QUINTANT_FIRST_NATURAL[old_id]}")
        print(f"    Palmer first_quintant = {palmer_origin.first_quintant}")
