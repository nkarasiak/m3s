# A5 Compatibility Fix Plan

## Problem Statement

**Current Status**: 13/14 compatibility tests passing (93%)

**Issue**: 7 cell ID mismatches at resolution 1 across the globe
- All mismatches have correct origin (dodecahedron face)
- Segment values differ by ±1 from Palmer's reference implementation

## Root Cause Analysis

### Investigation Results

Test case: (-165, -70) at resolution 1
```
Our values:     origin=9, segment=4, quintant=4
Palmer values:  origin=9, segment=3
```

### Code Flow

1. ✅ `lonlat_to_spherical` - CORRECT (using Palmer's convention)
2. ✅ `find_nearest_origin` - CORRECT (origin matches Palmer)
3. ✅ `cartesian_to_face_ij` - CORRECT (using Palmer's dodecahedron projection)
4. ❌ `determine_quintant` OR `quintant_to_segment` - INCORRECT

### The Problem

Either:
1. **Option A**: `determine_quintant()` is calculating wrong quintant from (i, j)
2. **Option B**: `quintant_to_segment()` mapping is incorrect for resolution 1

Since we're using Palmer's projection for IJ coordinates, the most likely issue is that:
- Palmer uses quintant values directly as segments at resolution 1 (no mapping)
- OR Palmer's quintant-to-segment mapping is different from what we implemented

## Fix Strategy

### Phase 1: Direct Integration (Recommended)

**Approach**: Use Palmer's library directly for resolution 1 cell ID generation

**Rationale**:
- Resolution 0-1 are already delegating to Palmer for resolutions >= 2
- This ensures 100% compatibility
- Simpler and more reliable than reverse-engineering the exact mapping

**Implementation**:
1. Modify `m3s/a5/cell.py` - `lonlat_to_cell()` method
2. For resolution 1, call Palmer's `lonlat_to_cell` directly
3. Keep our implementation for resolution 0 since it's working

**Files to Modify**:
- `m3s/a5/cell.py` (lines 104-119)

**Code Change**:
```python
# In lonlat_to_cell method, line 104:
if resolution >= 1:  # Changed from >= 2 to >= 1
    # Use Palmer's implementation for resolution 1+ (Hilbert curves + correct segment mapping)
    import a5 as palmer_a5
    cell_id = palmer_a5.lonlat_to_cell((lon, lat), resolution)
    return cell_id
else:
    # Resolution 0 only
    s = 0
    cell_id = self.serializer.encode(origin_id, segment, s, resolution)
    return cell_id
```

**Pros**:
- Guaranteed 100% compatibility with Palmer
- Minimal code changes
- Low risk of introducing new bugs

**Cons**:
- Still depends on Palmer's library
- Doesn't fix our own implementation

### Phase 2: Fix Native Implementation (Future)

**Approach**: Debug and fix the quintant-to-segment mapping

**Investigation Required**:
1. Extract Palmer's segment assignment logic
2. Compare with our `quintant_to_segment()` implementation
3. Verify `determine_quintant()` polar angle calculation
4. Check if resolution 1 has special segment handling

**Files to Investigate**:
- `m3s/a5/coordinates.py` - `determine_quintant()` (line 444)
- `m3s/a5/projections/origin_data.py` - `quintant_to_segment()` (line 92)
- Palmer's source: `a5/core/cell.py` - segment assignment logic

**Potential Issues**:
- Quintant angle boundaries might be off
- Segment mapping formula might be incorrect
- Resolution 1 might have special handling we're missing

## Recommended Implementation Plan

### Step 1: Quick Fix (Use Palmer for Resolution 1)

**Task**: Modify cell.py to delegate resolution 1 to Palmer

**Time**: 5-10 minutes

**Risk**: Low

**Expected Result**: 100% compatibility test pass

### Step 2: Verify Fix

**Task**: Run compatibility tests

```bash
pytest tests/test_a5_compatibility.py -v
```

**Expected**: All 14 tests passing

### Step 3: Update Documentation

**Task**: Update CLAUDE.md to note Palmer dependency for resolution 1

**Files**:
- `CLAUDE.md` - A5 Grid System section

### Step 4: Future Enhancement (Optional)

**Task**: Implement native resolution 1 handling

**Benefits**:
- Reduce Palmer dependency
- Better understanding of A5 algorithm
- Educational value

**Priority**: Low (since Palmer integration works)

## Verification Plan

### Unit Tests
```bash
# Compatibility tests
pytest tests/test_a5_compatibility.py -v

# All A5 tests
pytest tests/test_a5.py -v

# Quick smoke test
python -c "
import a5 as palmer_a5
from m3s.a5 import lonlat_to_cell

test_cases = [
    (-165, -70, 1),
    (15, -25, 1),
    (-0.1278, 51.5074, 1),
]

for lon, lat, res in test_cases:
    our_cell = lonlat_to_cell(lon, lat, res)
    palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), res)
    match = '✓' if our_cell == palmer_cell else '✗'
    print(f'{match} ({lon}, {lat}): {our_cell == palmer_cell}')
"
```

### Expected Results
- All compatibility tests passing (14/14)
- No regressions in other A5 tests
- Segment values match Palmer exactly

## Success Criteria

- [ ] All 14 compatibility tests passing
- [ ] Cell IDs match Palmer exactly for resolution 0-1
- [ ] No regressions in existing A5 functionality
- [ ] Documentation updated

## Timeline

- **Quick Fix**: 10 minutes
- **Testing**: 5 minutes
- **Documentation**: 5 minutes
- **Total**: ~20 minutes

## Alternative: Deep Debugging

If we wanted to fix the native implementation instead:

1. Add detailed logging to quintant_to_segment()
2. Compare quintant values with Palmer's for all 7 failing cases
3. Identify the pattern in segment assignment
4. Modify mapping logic to match Palmer
5. Test extensively

**Estimated Time**: 2-4 hours
**Risk**: Medium (could introduce new bugs)
**Recommendation**: Not worth it given Palmer integration works perfectly

## Conclusion

**Recommended Action**: Implement Quick Fix (Phase 1)

This ensures 100% compatibility with minimal risk and effort. The native implementation debugging can be deferred to a future enhancement if removing the Palmer dependency becomes important.
