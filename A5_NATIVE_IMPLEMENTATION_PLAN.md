# A5 Native Implementation Plan - 60/60 Tests Passing

## Current Status
- **Passing**: 43/60 (72%)
- **Failing**: 17/60 (28%)
- **Palmer Dependency**: Currently using Palmer's library for resolution 1+

## Goal
**Achieve 60/60 tests passing with ZERO Palmer dependencies**

## Failure Analysis

### Category 1: Error Message Mismatches (Easy - 3 tests)
**Effort**: 5 minutes each
**Files**: `m3s/a5/constants.py`

1. `test_init_invalid_precision` - Wrong error message
   - Expected: "A5 precision must be between 0 and 30"
   - Actual: "Resolution must be between 0 and 30"
   - Fix: Update error message in validation function

2. `test_get_cell_from_identifier_invalid` - Wrong error message
   - Similar error message mismatch
   - Fix: Update error message

3. `test_a5_error_handling` - Wrong error message
   - Expected: "A5 precision"
   - Actual: "Resolution"
   - Fix: Same as above

**Fix Strategy**: Update `constants.py` validation functions to use "A5 precision" instead of "Resolution"

### Category 2: Palmer Import Dependency (Critical - 4 tests)
**Effort**: 4-6 hours total
**Files**: `m3s/a5/cell.py`, `m3s/a5/hilbert.py` (new)

1. `test_cell_to_lonlat` - Uses Palmer for cell_to_lonlat
2. `test_cell_to_children` - Uses Palmer for get_children
3. `test_cell_area` - Depends on Palmer-generated cells
4. `test_roundtrip_conversions` - Uses Palmer for roundtrip

**Root Cause**: Currently delegating to Palmer for:
- Resolution 1+ cell ID generation (quintant-to-segment mapping)
- Resolution 2+ Hilbert curve S-value calculation
- cell_to_lonlat reverse conversion
- cell_to_boundary polygon generation

**Fix Strategy**:
1. Implement native quintant-to-segment mapping for resolution 1
2. Implement native Hilbert curve for resolution 2+
3. Implement native cell_to_lonlat (inverse projection)
4. Implement native cell_to_boundary (pentagon vertex generation)

### Category 3: Pole/Edge Cases (Medium - 2 tests)
**Effort**: 1-2 hours
**Files**: `m3s/a5/cell.py`, `m3s/a5/geometry.py`

1. `test_get_cell_from_point_various_locations` - Pole containment fails
   - North/South pole cells don't contain the pole point
   - Polygon distance is >30 degrees
   - Fix: Special handling for pole cells

2. `test_polygon_validity` - Too many polygon vertices
   - Expected: 6 vertices (pentagon + closing)
   - Actual: 21 vertices
   - Fix: Simplify polygon generation, remove over-tessellation

**Fix Strategy**:
- Add pole detection in cell_to_boundary
- Simplify polygon vertex generation
- Ensure pole points are properly contained

### Category 4: Expected Value Mismatches (Medium - 5 tests)
**Effort**: 30 minutes each
**Files**: Various

1. `test_neighbors` - Wrong neighbor count
   - Expected: exactly 5
   - Actual: 7
   - Fix: Refine neighbor finding algorithm

2. `test_coordinate_transformations` - Missing attributes
   - Tests expect access to internal `_transformer` attribute
   - Fix: Either expose attribute or skip internal tests

3. `test_pentagon_vertex_generation` - Missing attributes
   - Tests expect access to internal `_pentagon` attribute
   - Fix: Same as above

4. `test_cell_encoding_decoding` - Missing attributes
   - Tests expect access to internal `_encode_cell_id` method
   - Fix: Same as above

5. `test_cell_to_parent_invalid_resolution` - Wrong error handling
   - Tests expect specific error for invalid parent
   - Fix: Update error handling

### Category 5: Missing Implementations (Hard - 3 tests)
**Effort**: 2-3 hours each
**Files**: `m3s/a5/cell.py`

1. `test_latlon_to_xyz_conversions` - Internal method access
   - Tests expect `_xyz_to_lonlat` method
   - Fix: Expose or implement public API

2. `test_xyz_coordinate_properties` - Internal method access
   - Tests expect `_xyz_normalize` or similar
   - Fix: Expose or implement public API

3. `test_cell_to_children_invalid_resolution` - Error handling
   - Tests expect specific exception for max resolution
   - Fix: Update error handling in get_children

## Implementation Plan

### Phase 1: Quick Wins (30 minutes)
**Goal**: Fix 3 error message tests

1. Update `m3s/a5/constants.py`:
   ```python
   def validate_resolution(resolution: int) -> None:
       if resolution < 0 or resolution > MAX_RESOLUTION:
           raise ValueError(
               f"A5 precision must be between 0 and {MAX_RESOLUTION}, got {resolution}"
           )
   ```

2. Run tests: Should get 46/60 passing (+3)

### Phase 2: Native Cell ID Generation (6 hours)
**Goal**: Remove Palmer dependency for cell ID generation

#### Step 2.1: Fix Resolution 1 Segment Mapping (2 hours)

**Investigation Required**:
- Understand Palmer's exact quintant-to-segment formula
- Compare with our current implementation
- Identify the +/-1 difference pattern

**Files to Modify**:
- `m3s/a5/projections/origin_data.py` - Fix `quintant_to_segment()`
- OR `m3s/a5/coordinates.py` - Fix `determine_quintant()`

**Approach**:
1. Extract Palmer's segment assignment from source code
2. Test with all 12 origins at resolution 1
3. Verify against Palmer's output
4. Update our mapping formula

**Test Cases**:
```python
# Known failing cases from compatibility tests
test_cases = [
    (-165, -70, 1, 9, 3),  # origin=9, expected segment=3
    (-165, -55, 1, 9, 3),
    (15, -25, 1, 3, 3),
    (-165, -10, 1, 11, 2),
    (15, -10, 1, 3, 3),
    (-165, 20, 1, 11, 1),
    (15, 65, 1, 0, 2),
]
```

#### Step 2.2: Implement Hilbert Curves for Resolution 2+ (4 hours)

**Challenge**: Hilbert curve mapping is complex

**Options**:
A. **Implement from scratch** (4-6 hours)
   - Study Hilbert curve algorithm
   - Implement IJ→Hilbert S-value conversion
   - Implement inverse Hilbert S→IJ conversion
   - Test thoroughly

B. **Use existing Hilbert library** (2 hours)
   - Install: `pip install hilbertcurve`
   - Adapt to our coordinate system
   - Test integration

C. **Simplified approach for testing** (1 hour)
   - Use Palmer's Hilbert code as reference
   - Copy core Hilbert algorithm (properly attributed)
   - Integrate into our system

**Recommended**: Option B (existing library)

**Implementation**:

Create `m3s/a5/hilbert.py`:
```python
"""Hilbert curve support for A5 resolutions 2+."""

from hilbertcurve.hilbertcurve import HilbertCurve

class A5HilbertCurve:
    """Hilbert curve for A5 grid subdivision."""

    def __init__(self, resolution: int):
        """Initialize Hilbert curve for given resolution."""
        # A5 uses 5-fold subdivision, not 4-fold
        # Each resolution level adds log2(5) ≈ 2.32 bits
        # For resolution r, need approximately r * log2(5) bits

        # Simplified: use 2D Hilbert curve on IJ plane
        # p = number of iterations (bits per dimension)
        # n = 2 (dimensions: I and J)
        p = resolution * 2  # Approximate
        n = 2

        self.curve = HilbertCurve(p, n)

    def ij_to_s(self, i: float, j: float) -> int:
        """Convert IJ coordinates to Hilbert S-value."""
        # Normalize IJ to integer grid
        # A5 uses [-1, 1] range for IJ
        # Map to [0, 2^p] integer range

        i_int = int((i + 1) * (2 ** (self.curve.p - 1)))
        j_int = int((j + 1) * (2 ** (self.curve.p - 1)))

        # Get Hilbert index
        s = self.curve.distance_from_coordinates([i_int, j_int])
        return s

    def s_to_ij(self, s: int) -> tuple[float, float]:
        """Convert Hilbert S-value back to IJ coordinates."""
        coords = self.curve.coordinates_from_distance(s)

        # Denormalize back to [-1, 1]
        i = (coords[0] / (2 ** (self.curve.p - 1))) - 1
        j = (coords[1] / (2 ** (self.curve.p - 1))) - 1

        return i, j
```

Update `m3s/a5/cell.py`:
```python
def lonlat_to_cell(self, lon: float, lat: float, resolution: int) -> int:
    # ... existing code for steps 1-6 ...

    if resolution >= 2:
        # Use native Hilbert curve implementation
        from m3s.a5.hilbert import A5HilbertCurve

        hilbert = A5HilbertCurve(resolution)
        s = hilbert.ij_to_s(i, j)
    elif resolution == 1:
        # Use native quintant-to-segment mapping
        quintant = self.transformer.determine_quintant(i, j)
        from m3s.a5.projections.origin_data import origins, quintant_to_segment
        origin = origins[origin_id]
        segment = quintant_to_segment(quintant, origin)
        s = 0  # No Hilbert subdivision at resolution 1
    else:
        # Resolution 0
        segment = 0
        s = 0

    cell_id = self.serializer.encode(origin_id, segment, s, resolution)
    return cell_id
```

**Tests**: Should fix 4-5 tests related to Palmer dependency

### Phase 3: Implement Reverse Operations (3 hours)
**Goal**: cell_to_lonlat and cell_to_boundary without Palmer

#### Step 3.1: Native cell_to_lonlat (1.5 hours)

**Implementation**:
```python
def cell_to_lonlat(self, cell_id: int) -> Tuple[float, float]:
    """Convert cell ID to center coordinates (native implementation)."""
    # Decode cell ID
    origin_id, segment, s, resolution = self.serializer.decode(cell_id)

    if resolution >= 2:
        # Use Hilbert curve to get IJ
        from m3s.a5.hilbert import A5HilbertCurve
        hilbert = A5HilbertCurve(resolution)
        i, j = hilbert.s_to_ij(s)
    elif resolution == 1:
        # Convert segment to quintant, then to IJ
        # (Inverse of quintant_to_segment)
        from m3s.a5.projections.origin_data import origins
        origin = origins[origin_id]
        quintant = segment_to_quintant(segment, origin)  # Need to implement

        # Convert quintant to IJ (polar coordinates)
        # Quintant n is at angle (2π/5) * n
        angle = (2 * math.pi / 5) * quintant
        r = 0.5  # Approximate radius for resolution 1
        i = r * math.cos(angle)
        j = r * math.sin(angle)
    else:
        # Resolution 0: center of face
        i, j = 0.0, 0.0

    # Convert IJ back to lonlat
    origin_xyz = self.dodec.get_origin_cartesian(origin_id)
    xyz = self.transformer.face_ij_to_cartesian(i, j, origin_xyz)
    lon, lat = self.transformer.cartesian_to_lonlat(xyz)

    return lon, lat
```

**New Helper Function**:
```python
def segment_to_quintant(segment: int, origin: Origin) -> int:
    """Inverse of quintant_to_segment."""
    # Reverse the quintant_to_segment formula
    # Original: segment = (origin.first_quintant + face_relative_quintant) % 5
    face_relative_quintant = (segment - origin.first_quintant + 5) % 5

    # Reverse: face_relative_quintant = (step * delta + 5) % 5
    # Need to solve for delta
    layout = origin.orientation
    is_clockwise = layout in (_CLOCKWISE_FAN, _CLOCKWISE_STEP)
    step = -1 if is_clockwise else 1

    # Inverse of: face_relative_quintant = (step * delta + 5) % 5
    delta = (face_relative_quintant * step + 5) % 5

    # Reverse: delta = (quintant - origin.first_quintant + 5) % 5
    quintant = (delta + origin.first_quintant) % 5

    return quintant
```

#### Step 3.2: Native cell_to_boundary (1.5 hours)

**Implementation**:
```python
def cell_to_boundary(self, cell_id: int) -> List[Tuple[float, float]]:
    """Get pentagon boundary vertices (native implementation)."""
    # Get cell center
    center_lon, center_lat = self.cell_to_lonlat(cell_id)

    # Get resolution to determine cell size
    _, _, _, resolution = self.serializer.decode(cell_id)

    # Pentagon has 5 vertices
    vertices = []

    # Calculate approximate cell radius
    # Each resolution subdivides by ~√5
    base_radius = 60.0  # degrees for resolution 0
    radius = base_radius / (math.sqrt(5) ** resolution)

    # Generate 5 vertices around center
    for i in range(5):
        angle = (2 * math.pi / 5) * i - math.pi / 2  # Start from top

        # Approximate vertex position
        # (This is simplified - real implementation needs geodesic calculation)
        vertex_lat = center_lat + radius * math.sin(angle)
        vertex_lon = center_lon + radius * math.cos(angle) / math.cos(math.radians(center_lat))

        # Clamp to valid range
        vertex_lat = max(-90, min(90, vertex_lat))
        vertex_lon = ((vertex_lon + 180) % 360) - 180

        vertices.append((vertex_lon, vertex_lat))

    # Close the polygon
    vertices.append(vertices[0])

    return vertices
```

**Better Approach** (use existing Pentagon geometry):
```python
def cell_to_boundary(self, cell_id: int) -> List[Tuple[float, float]]:
    """Get pentagon boundary vertices using proper projection."""
    # Decode cell ID
    origin_id, segment, s, resolution = self.serializer.decode(cell_id)

    # Get cell center in IJ coordinates
    if resolution >= 2:
        from m3s.a5.hilbert import A5HilbertCurve
        hilbert = A5HilbertCurve(resolution)
        center_i, center_j = hilbert.s_to_ij(s)
    elif resolution == 1:
        # ... get IJ from segment ...
        pass
    else:
        center_i, center_j = 0.0, 0.0

    # Calculate cell size at this resolution
    cell_size = 2.0 / (5 ** (resolution / 2))  # Approximate

    # Generate pentagon vertices in IJ space
    vertices_ij = []
    for i in range(5):
        angle = (2 * math.pi / 5) * i
        vi = center_i + cell_size * math.cos(angle)
        vj = center_j + cell_size * math.sin(angle)
        vertices_ij.append((vi, vj))

    # Project vertices to lonlat
    origin_xyz = self.dodec.get_origin_cartesian(origin_id)
    vertices_lonlat = []

    for vi, vj in vertices_ij:
        xyz = self.transformer.face_ij_to_cartesian(vi, vj, origin_xyz)
        lon, lat = self.transformer.cartesian_to_lonlat(xyz)
        vertices_lonlat.append((lon, lat))

    # Close polygon
    vertices_lonlat.append(vertices_lonlat[0])

    return vertices_lonlat
```

### Phase 4: Fix Expected Value Mismatches (2 hours)
**Goal**: Fix tests expecting specific values/attributes

1. **test_neighbors** - Neighbor count
   - Current: Returns 7 neighbors
   - Expected: Exactly 5
   - Fix: Tighten neighbor finding to only return true edge-adjacent cells

2. **Internal attribute tests** - 3 tests
   - Options:
     A. Expose internal attributes as public properties
     B. Mark tests as testing implementation details (skip or modify)
   - Recommended: Expose as properties

3. **Error handling tests** - 2 tests
   - Update error messages and validation

### Phase 5: Fix Pole Cases (2 hours)
**Goal**: Handle North/South poles correctly

1. Add pole detection
2. Special polygon generation for polar cells
3. Ensure pole points are contained in polar cells

### Phase 6: Final Integration & Testing (2 hours)
**Goal**: 60/60 passing

1. Run full test suite
2. Fix any remaining issues
3. Performance optimization
4. Documentation updates

## Total Effort Estimate

- Phase 1 (Error messages): 30 minutes
- Phase 2 (Native cell ID): 6 hours
- Phase 3 (Reverse operations): 3 hours
- Phase 4 (Value mismatches): 2 hours
- Phase 5 (Pole cases): 2 hours
- Phase 6 (Integration): 2 hours

**Total: ~15-16 hours of focused development**

## Success Criteria

- [ ] All 60/60 tests passing
- [ ] Zero imports from `a5` (Palmer's library)
- [ ] Native implementation for all resolutions (0-30)
- [ ] All compatibility tests still passing (14/14)
- [ ] No performance regressions
- [ ] Code well-documented

## Risk Mitigation

1. **Complexity Risk**: Hilbert curves are complex
   - Mitigation: Use existing hilbertcurve library
   - Fallback: Study Palmer's implementation more deeply

2. **Time Risk**: 15+ hours is significant
   - Mitigation: Implement in phases, test incrementally
   - Fallback: Can stop after Phase 2 if time-constrained

3. **Compatibility Risk**: Breaking existing functionality
   - Mitigation: Run full test suite after each phase
   - Fallback: Git branches for easy rollback

## Next Steps

1. Start with Phase 1 (quick wins)
2. Tackle Phase 2 (critical path - native cell IDs)
3. Proceed through remaining phases systematically

Ready to begin implementation?
