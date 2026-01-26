# A5 Full Native Implementation Plan
## Complete 60/60 Test Pass Without Palmer Dependencies

**Created:** 2026-01-25
**Status:** Ready for Implementation
**Estimated Total Effort:** 40-50 hours

---

## Executive Summary

This plan provides a complete roadmap to achieve 60/60 A5 test passes with zero dependencies on Palmer's a5-py library. The implementation requires deep understanding of spherical geometry, dodecahedral projections, and Hilbert space-filling curves.

**Current Status:**
- Tests Passing: 39/60 (65%)
- Tests Failing: 21/60 (35%)
- Palmer Dependencies: Partial (reverse operations only)

**Goal:**
- Tests Passing: 60/60 (100%)
- Palmer Dependencies: None
- Performance: Acceptable (< 2x Palmer speed)

---

## Table of Contents

1. [Problem Analysis](#problem-analysis)
2. [Technical Architecture](#technical-architecture)
3. [Implementation Phases](#implementation-phases)
4. [Phase Details](#phase-details)
5. [Testing Strategy](#testing-strategy)
6. [Success Criteria](#success-criteria)
7. [Risk Mitigation](#risk-mitigation)
8. [Timeline](#timeline)

---

## Problem Analysis

### Current Implementation State

**What Works:**
- ✅ Forward cell ID generation (lonlat → cell_id) for all resolutions
- ✅ Hilbert curve forward mapping (IJ → S)
- ✅ Basic API structure and error handling
- ✅ Grid system integration (M3S BaseGrid interface)

**What Fails:**
- ❌ Reverse cell ID to coordinates (cell_id → lonlat) - 10-30° errors
- ❌ Reverse Hilbert mapping (S → IJ) - accuracy issues
- ❌ Reverse dodecahedral projection (XYZ → IJ) - not implemented
- ❌ Pentagon boundary generation - oversimplified
- ❌ Cell hierarchy (parent/child) - sampling-based, incomplete

### Root Causes

1. **Dodecahedral Projection Complexity**
   - Forward: lonlat → spherical → XYZ → IJ (using Palmer's projection)
   - Reverse: IJ → XYZ → spherical → lonlat (NOT IMPLEMENTED)
   - Missing: Inverse gnomonic projection for each dodecahedron face

2. **Hilbert Curve Bidirectionality**
   - Forward: Working with bit-interleaving algorithm
   - Reverse: Working but calibration issues with resolution scaling
   - Missing: Exact bit-width calculation per resolution

3. **Quintant-Segment Mapping**
   - Forward: quintant_to_segment() works
   - Reverse: segment_to_quintant() not properly implemented
   - Missing: Inverse winding direction calculation

4. **Pentagon Geometry**
   - Current: Simplified circular approximation
   - Needed: Proper pentagonal tessellation with correct vertex positions
   - Missing: Edge length calculation, vertex angle determination

### Failing Test Categories

| Category | Count | Complexity | Estimated Effort |
|----------|-------|------------|------------------|
| Reverse projection accuracy | 4 | High | 20 hours |
| Pole/edge cases | 2 | Medium | 8 hours |
| Pentagon boundary | 2 | Medium | 6 hours |
| Cell hierarchy | 3 | Medium | 8 hours |
| Internal attributes | 5 | Low | 4 hours |
| Neighbors refinement | 1 | Low | 2 hours |
| Error handling | 4 | Low | 2 hours |
| **TOTAL** | **21** | - | **50 hours** |

---

## Technical Architecture

### Coordinate System Chain

```
Geographic (lon, lat)
    ↕ (lonlat_to_spherical / spherical_to_lonlat)
Spherical (θ, φ)
    ↕ (spherical_to_cartesian / cartesian_to_spherical)
Cartesian (x, y, z)
    ↕ (cartesian_to_face_ij / face_ij_to_cartesian) ← NEEDS FIXING
Face IJ (i, j)
    ↕ (ij_to_quintant / quintant_to_ij)
Quintant (0-4)
    ↕ (quintant_to_segment / segment_to_quintant) ← NEEDS FIXING
Segment (0-4)
    ↕ (ij_to_hilbert / hilbert_to_ij) [resolution >= 2]
Hilbert S-value
    ↕ (encode / decode)
Cell ID (64-bit)
```

**Critical Missing Links:**
1. `face_ij_to_cartesian` - Inverse gnomonic projection
2. `segment_to_quintant` - Reverse winding calculation
3. `hilbert_to_ij` - Proper S→IJ with correct scaling

### Dodecahedral Projection Mathematics

The dodecahedron has 12 pentagonal faces. Each face uses a gnomonic projection.

#### Forward Projection (XYZ → IJ)

**Current Implementation:** Using Palmer's `_dodecahedron.forward()`

**Mathematical Formula:**
```python
def gnomonic_forward(xyz: np.ndarray, origin_xyz: np.ndarray) -> Tuple[float, float]:
    """
    Project 3D point onto 2D face plane using gnomonic projection.

    Gnomonic projection: Project from sphere center through point onto tangent plane.
    """
    # Create local coordinate system for the face
    face_normal = origin_xyz / np.linalg.norm(origin_xyz)

    # Create orthonormal basis on the face
    # Basis vectors must be tangent to the sphere at origin
    if abs(face_normal[2]) < 0.9:
        up = np.array([0, 0, 1])
    else:
        up = np.array([1, 0, 0])

    basis_i = np.cross(face_normal, up)
    basis_i /= np.linalg.norm(basis_i)

    basis_j = np.cross(face_normal, basis_i)
    basis_j /= np.linalg.norm(basis_j)

    # Project point onto tangent plane
    # Scale factor: dot product with face normal gives projection distance
    scale = np.dot(xyz, face_normal)

    # Project onto plane
    projected = xyz / scale

    # Get IJ coordinates in local basis
    i = np.dot(projected - origin_xyz, basis_i)
    j = np.dot(projected - origin_xyz, basis_j)

    return i, j
```

#### Reverse Projection (IJ → XYZ)

**Current Implementation:** Incorrect - produces large errors

**Needed Implementation:**
```python
def gnomonic_reverse(i: float, j: float, origin_xyz: np.ndarray) -> np.ndarray:
    """
    Project 2D face coordinates back to 3D sphere.

    Inverse gnomonic projection.
    """
    # Recreate local basis (same as forward)
    face_normal = origin_xyz / np.linalg.norm(origin_xyz)

    if abs(face_normal[2]) < 0.9:
        up = np.array([0, 0, 1])
    else:
        up = np.array([1, 0, 0])

    basis_i = np.cross(face_normal, up)
    basis_i /= np.linalg.norm(basis_i)

    basis_j = np.cross(face_normal, basis_i)
    basis_j /= np.linalg.norm(basis_j)

    # Construct point on tangent plane
    point_on_plane = origin_xyz + i * basis_i + j * basis_j

    # Project from center through point to sphere
    # Normalize to unit sphere
    xyz = point_on_plane / np.linalg.norm(point_on_plane)

    return xyz
```

**Key Insight:** The inverse is NOT simply reversing the dot products. It requires:
1. Reconstructing the tangent plane point from IJ
2. Normalizing to project back onto unit sphere

### Hilbert Curve Exact Specification

#### Bit Width Calculation

For A5 serialization format:
```python
FIRST_HILBERT_RESOLUTION = 2  # Hilbert starts at resolution 2

def get_hilbert_bits(resolution: int) -> int:
    """
    Calculate exact number of Hilbert bits for resolution.

    From serialization.py:
    - hilbert_levels = resolution - FIRST_HILBERT_RESOLUTION + 1
    - hilbert_bits = 2 * hilbert_levels

    For resolution 2: hilbert_levels = 1, hilbert_bits = 2
    For resolution 3: hilbert_levels = 2, hilbert_bits = 4
    For resolution 4: hilbert_levels = 3, hilbert_bits = 6
    ...
    For resolution 30: hilbert_levels = 29, hilbert_bits = 58
    """
    if resolution < FIRST_HILBERT_RESOLUTION:
        return 0

    hilbert_levels = resolution - FIRST_HILBERT_RESOLUTION + 1
    hilbert_bits = 2 * hilbert_levels
    return hilbert_bits

def get_grid_size(resolution: int) -> int:
    """
    Calculate grid size for Hilbert curve.

    grid_size = 2^p where p = bits per dimension
    hilbert_bits = 2*p (for 2D)
    Therefore: p = hilbert_bits / 2 = hilbert_levels
    """
    hilbert_levels = resolution - FIRST_HILBERT_RESOLUTION + 1
    p = hilbert_levels
    grid_size = 2 ** p
    return grid_size
```

#### IJ Normalization

Current issue: IJ coordinates in range [-1, 1] but grid is [0, grid_size-1]

**Correct Normalization:**
```python
def normalize_ij_to_grid(i: float, j: float, grid_size: int) -> Tuple[int, int]:
    """
    Normalize IJ coordinates from [-1, 1] to [0, grid_size-1].

    Key: Preserve the sign and scale correctly.
    """
    # Shift from [-1, 1] to [0, 2]
    i_shifted = i + 1.0
    j_shifted = j + 1.0

    # Scale to [0, grid_size-1]
    i_scaled = i_shifted * (grid_size - 1) / 2.0
    j_scaled = j_shifted * (grid_size - 1) / 2.0

    # Round to integers
    i_int = int(round(i_scaled))
    j_int = int(round(j_scaled))

    # Clamp to valid range
    i_int = max(0, min(grid_size - 1, i_int))
    j_int = max(0, min(grid_size - 1, j_int))

    return i_int, j_int

def denormalize_grid_to_ij(i_int: int, j_int: int, grid_size: int) -> Tuple[float, float]:
    """
    Denormalize grid coordinates back to IJ in [-1, 1].

    Exact inverse of normalize_ij_to_grid.
    """
    # Scale from [0, grid_size-1] to [0, 2]
    i_scaled = (i_int * 2.0) / (grid_size - 1)
    j_scaled = (j_int * 2.0) / (grid_size - 1)

    # Shift from [0, 2] to [-1, 1]
    i = i_scaled - 1.0
    j = j_scaled - 1.0

    return i, j
```

### Quintant-Segment Inverse

**Current Forward Implementation:**
```python
def quintant_to_segment(quintant: int, origin: Origin) -> int:
    layout = origin.orientation
    is_clockwise = layout in (_CLOCKWISE_FAN, _CLOCKWISE_STEP)
    step = -1 if is_clockwise else 1

    delta = (quintant - origin.first_quintant + 5) % 5
    face_relative_quintant = (step * delta + 5) % 5
    segment = (origin.first_quintant + face_relative_quintant) % 5

    return segment
```

**Needed Reverse Implementation:**
```python
def segment_to_quintant(segment: int, origin: Origin) -> int:
    """
    Inverse of quintant_to_segment.

    Given: segment = (origin.first_quintant + face_relative_quintant) % 5
    Solve for: quintant

    Steps:
    1. face_relative_quintant = (segment - origin.first_quintant + 5) % 5
    2. face_relative_quintant = (step * delta + 5) % 5
       → delta = (face_relative_quintant - 0 + 5) % 5 if step == 1
       → delta = (0 - face_relative_quintant + 5) % 5 if step == -1
    3. delta = (quintant - origin.first_quintant + 5) % 5
       → quintant = (delta + origin.first_quintant) % 5
    """
    layout = origin.orientation
    is_clockwise = layout in (_CLOCKWISE_FAN, _CLOCKWISE_STEP)
    step = -1 if is_clockwise else 1

    # Step 1: Reverse segment encoding
    face_relative_quintant = (segment - origin.first_quintant + 5) % 5

    # Step 2: Reverse winding transformation
    if step == 1:
        # Counterclockwise: face_relative_quintant = delta
        delta = face_relative_quintant
    else:
        # Clockwise: face_relative_quintant = (-delta + 5) % 5
        # Reverse: delta = (-face_relative_quintant + 5) % 5
        delta = (-face_relative_quintant + 5) % 5

    # Step 3: Reverse quintant offset
    quintant = (delta + origin.first_quintant) % 5

    return quintant
```

**Verification Test:**
```python
# Test that forward and reverse are inverses
for origin_id in range(12):
    origin = origins[origin_id]
    for quintant in range(5):
        segment = quintant_to_segment(quintant, origin)
        recovered_quintant = segment_to_quintant(segment, origin)
        assert quintant == recovered_quintant, \
            f"Mismatch: origin={origin_id}, quintant={quintant}, " \
            f"segment={segment}, recovered={recovered_quintant}"
```

---

## Implementation Phases

### Phase 1: Fix Reverse Dodecahedral Projection (20 hours)

**Goal:** Accurate IJ → XYZ → lonlat conversion

**Tasks:**
1. Implement `gnomonic_reverse()` in `coordinates.py`
2. Update `face_ij_to_cartesian()` to use gnomonic reverse
3. Test roundtrip: lonlat → XYZ → IJ → XYZ → lonlat
4. Validate accuracy to < 0.01° error

**Files:**
- `m3s/a5/coordinates.py`
- `m3s/a5/geometry.py`

**Testing:**
```python
def test_roundtrip_projection():
    """Test that projection is invertible."""
    transformer = CoordinateTransformer()
    dodec = Dodecahedron()

    test_points = [
        (0.0, 0.0),
        (45.0, 45.0),
        (-120.0, -60.0),
        (179.0, 89.0),
    ]

    for lon, lat in test_points:
        # Forward
        theta, phi = transformer.lonlat_to_spherical(lon, lat)
        xyz = transformer.spherical_to_cartesian(theta, phi)
        origin_id = dodec.find_nearest_origin((theta, phi))
        origin_xyz = dodec.get_origin_cartesian(origin_id)
        i, j = transformer.cartesian_to_face_ij(xyz, origin_xyz, origin_id)

        # Reverse
        xyz_recovered = transformer.face_ij_to_cartesian(i, j, origin_xyz)
        lon_recovered, lat_recovered = transformer.cartesian_to_lonlat(xyz_recovered)

        # Verify
        error_lon = abs(lon_recovered - lon)
        error_lat = abs(lat_recovered - lat)

        # Handle antimeridian
        if error_lon > 180:
            error_lon = 360 - error_lon

        assert error_lon < 0.01, f"Lon error: {error_lon}°"
        assert error_lat < 0.01, f"Lat error: {error_lat}°"
```

### Phase 2: Fix Segment-Quintant Inverse (4 hours)

**Goal:** Accurate segment → quintant conversion

**Tasks:**
1. Implement `segment_to_quintant()` in `origin_data.py`
2. Add verification tests for all 12 origins
3. Update `cell_to_lonlat()` to use correct segment→quintant

**Files:**
- `m3s/a5/projections/origin_data.py`
- `m3s/a5/cell.py`

### Phase 3: Fix Hilbert Reverse Mapping (8 hours)

**Goal:** Accurate S → IJ conversion with proper scaling

**Tasks:**
1. Fix `get_grid_size()` calculation in `hilbert.py`
2. Fix `denormalize_grid_to_ij()` to match forward normalization
3. Test roundtrip: IJ → S → IJ for all resolutions 2-10
4. Validate with Palmer's output

**Files:**
- `m3s/a5/hilbert.py`

**Testing:**
```python
def test_hilbert_roundtrip():
    """Test Hilbert curve bidirectionality."""
    for resolution in range(2, 11):
        curve = A5HilbertCurve(resolution)

        # Test corners and center
        test_ij = [
            (-1.0, -1.0),
            (-1.0, 1.0),
            (1.0, -1.0),
            (1.0, 1.0),
            (0.0, 0.0),
        ]

        for i, j in test_ij:
            s = curve.ij_to_s(i, j)
            i_recovered, j_recovered = curve.s_to_ij(s)

            error_i = abs(i_recovered - i)
            error_j = abs(j_recovered - j)

            # Allow small rounding error due to grid quantization
            max_error = 2.0 / curve.grid_size

            assert error_i < max_error, \
                f"res={resolution}, i error: {error_i} > {max_error}"
            assert error_j < max_error, \
                f"res={resolution}, j error: {error_j} > {max_error}"
```

### Phase 4: Implement cell_to_lonlat (6 hours)

**Goal:** Complete native cell_to_lonlat with all fixes integrated

**Tasks:**
1. Integrate Phase 1-3 fixes
2. Implement proper resolution 0, 1, 2+ handling
3. Test against Palmer's output for accuracy
4. Optimize for performance

**Files:**
- `m3s/a5/cell.py`

**Implementation:**
```python
def cell_to_lonlat(self, cell_id: int) -> Tuple[float, float]:
    """Convert cell ID to center coordinates (NATIVE - NO PALMER)."""
    import math

    # Decode cell ID
    origin_id, segment, s, resolution = self.serializer.decode(cell_id)

    # Get IJ coordinates based on resolution
    if resolution >= 2:
        # Use Hilbert curve (with Phase 3 fixes)
        from m3s.a5.hilbert import A5HilbertCurve
        hilbert = A5HilbertCurve(resolution)
        i, j = hilbert.s_to_ij(s)

    elif resolution == 1:
        # Use segment→quintant (with Phase 2 fixes)
        from m3s.a5.projections.origin_data import origins, segment_to_quintant
        origin = origins[origin_id]
        quintant = segment_to_quintant(segment, origin)

        # Convert quintant to IJ
        angle = (2 * math.pi / 5) * quintant
        r = 0.5  # Will be calibrated in testing
        i = r * math.cos(angle)
        j = r * math.sin(angle)

    else:
        # Resolution 0: center of face
        i, j = 0.0, 0.0

    # Project IJ → XYZ (with Phase 1 fixes)
    origin_xyz = self.dodec.get_origin_cartesian(origin_id)
    xyz = self.transformer.face_ij_to_cartesian(i, j, origin_xyz)  # FIXED

    # Convert XYZ → lonlat
    lon, lat = self.transformer.cartesian_to_lonlat(xyz)

    return lon, lat
```

### Phase 5: Implement cell_to_boundary (6 hours)

**Goal:** Accurate pentagon boundary generation

**Tasks:**
1. Calculate correct pentagon vertex positions
2. Use proper edge length scaling per resolution
3. Project vertices using fixed dodecahedral projection
4. Handle pole cases

**Files:**
- `m3s/a5/cell.py`
- `m3s/a5/geometry.py`

**Pentagon Vertex Calculation:**
```python
def cell_to_boundary(self, cell_id: int) -> List[Tuple[float, float]]:
    """Generate pentagon boundary (NATIVE - NO PALMER)."""
    import math

    # Get cell center in IJ space (using Phase 4 logic)
    origin_id, segment, s, resolution = self.serializer.decode(cell_id)

    if resolution >= 2:
        from m3s.a5.hilbert import A5HilbertCurve
        hilbert = A5HilbertCurve(resolution)
        center_i, center_j = hilbert.s_to_ij(s)
    elif resolution == 1:
        from m3s.a5.projections.origin_data import origins, segment_to_quintant
        origin = origins[origin_id]
        quintant = segment_to_quintant(segment, origin)
        angle = (2 * math.pi / 5) * quintant
        r = 0.5
        center_i = r * math.cos(angle)
        center_j = r * math.sin(angle)
    else:
        center_i, center_j = 0.0, 0.0

    # Calculate pentagon size
    # Pentagon side length = 2 * radius * sin(π/5)
    # Radius decreases by √5 each resolution
    base_radius = 1.0  # Will be calibrated
    radius = base_radius / (math.sqrt(5) ** resolution)

    # Generate 5 vertices
    vertices_ij = []
    for k in range(5):
        # Pentagon with one vertex pointing up
        angle = (2 * math.pi / 5) * k - math.pi / 2
        vertex_i = center_i + radius * math.cos(angle)
        vertex_j = center_j + radius * math.sin(angle)
        vertices_ij.append((vertex_i, vertex_j))

    # Project to lonlat (using Phase 1 fixed projection)
    origin_xyz = self.dodec.get_origin_cartesian(origin_id)
    vertices_lonlat = []

    for vi, vj in vertices_ij:
        xyz = self.transformer.face_ij_to_cartesian(vi, vj, origin_xyz)  # FIXED
        lon, lat = self.transformer.cartesian_to_lonlat(xyz)
        vertices_lonlat.append((lon, lat))

    # Close polygon
    vertices_lonlat.append(vertices_lonlat[0])

    return vertices_lonlat
```

### Phase 6: Fix Cell Hierarchy (8 hours)

**Goal:** Accurate parent/child relationships

**Tasks:**
1. Implement proper `get_parent()` using Hilbert tree structure
2. Implement proper `get_children()` using Hilbert subdivision
3. Test hierarchical consistency

**Parent Calculation:**
```python
def get_parent(self, cell_id: int) -> int:
    """Get parent cell (NATIVE - NO PALMER)."""
    origin_id, segment, s, resolution = self.serializer.decode(cell_id)

    if resolution == 0:
        raise ValueError("Cell at resolution 0 has no parent")

    parent_resolution = resolution - 1

    if parent_resolution == 0:
        # Parent is entire face
        parent_segment = 0
        parent_s = 0
    elif parent_resolution == 1:
        # Parent has same segment, no Hilbert
        parent_segment = segment
        parent_s = 0
    else:
        # Hilbert parent: S-value divided by 4 (2 bits per dimension)
        parent_segment = segment
        parent_s = s >> 2  # Divide by 4 (remove 2 bits)

    return self.serializer.encode(origin_id, parent_segment, parent_s, parent_resolution)
```

**Children Calculation:**
```python
def get_children(self, cell_id: int) -> List[int]:
    """Get child cells (NATIVE - NO PALMER)."""
    origin_id, segment, s, resolution = self.serializer.decode(cell_id)

    if resolution >= 30:
        raise ValueError("Cell at maximum resolution has no children")

    child_resolution = resolution + 1

    if child_resolution == 1:
        # Resolution 0 → 1: Create 5 children (one per segment)
        children = []
        for child_segment in range(5):
            child_id = self.serializer.encode(origin_id, child_segment, 0, child_resolution)
            children.append(child_id)
        return children

    elif child_resolution == 2:
        # Resolution 1 → 2: Each segment gets Hilbert cells
        # First Hilbert level has 4 cells (2x2 grid)
        children = []
        for child_s in range(4):
            child_id = self.serializer.encode(origin_id, segment, child_s, child_resolution)
            children.append(child_id)
        return children

    else:
        # Resolution >= 2: Hilbert subdivision
        # Each Hilbert cell subdivides into 4 children
        children = []
        base_s = s << 2  # Multiply by 4 (add 2 bits)
        for offset in range(4):
            child_s = base_s + offset
            child_id = self.serializer.encode(origin_id, segment, child_s, child_resolution)
            children.append(child_id)
        return children
```

### Phase 7: Fix Pole Cases (8 hours)

**Goal:** Proper handling of North/South pole cells

**Tasks:**
1. Detect polar cells (latitude > 85° or < -85°)
2. Special boundary generation for polar pentagons
3. Ensure pole point containment

**Implementation:**
```python
def is_polar_cell(self, cell_id: int) -> bool:
    """Check if cell contains a pole."""
    lon, lat = self.cell_to_lonlat(cell_id)
    return abs(lat) > 85.0

def cell_to_boundary_polar(self, cell_id: int) -> List[Tuple[float, float]]:
    """
    Generate boundary for polar cells.

    Polar cells are special because they wrap around the pole.
    """
    lon, lat = self.cell_to_lonlat(cell_id)

    # Determine which pole
    is_north = lat > 0

    # Generate vertices in a circle around the pole
    vertices = []
    for k in range(36):  # More vertices for smooth curve
        angle = (2 * math.pi / 36) * k

        # Calculate latitude offset from pole
        # This will be calibrated based on cell size
        lat_offset = 5.0  # degrees, will be resolution-dependent

        vertex_lat = (90.0 - lat_offset) if is_north else (-90.0 + lat_offset)
        vertex_lon = (360.0 / 36) * k - 180.0

        vertices.append((vertex_lon, vertex_lat))

    # Close polygon
    vertices.append(vertices[0])

    return vertices
```

### Phase 8: Fix Internal Attributes & Neighbor Count (6 hours)

**Goal:** Expose necessary internal methods, refine neighbor finding

**Tasks:**
1. Expose `_transformer`, `_pentagon` as properties
2. Implement `quintant_to_ij()` and `ij_to_quintant()` methods
3. Refine neighbor finding to return exactly 5 neighbors

**Neighbor Refinement:**
```python
def get_neighbors(self, cell: GridCell) -> List[GridCell]:
    """
    Get exactly 5 neighbors for pentagonal cells.

    Pentagon neighbors share an edge, not just a vertex.
    """
    # Current implementation returns 4-7
    # Need to filter to only edge-adjacent cells

    candidates = self._get_neighbor_candidates(cell)

    # Filter to true edge-adjacent cells
    # Two cells are edge-adjacent if they share at least 2 vertices
    verified_neighbors = []

    for candidate in candidates:
        shared_vertices = count_shared_vertices(cell, candidate)
        if shared_vertices >= 2:
            verified_neighbors.append(candidate)

    # Pentagons should have exactly 5 neighbors
    # If we get 4 or 6, we're at a boundary or pole
    return verified_neighbors
```

### Phase 9: Final Error Handling (2 hours)

**Goal:** Match all expected error messages

**Tasks:**
1. Update `get_parent()` error for max resolution
2. Update `get_children()` error for max resolution
3. Ensure all ValueError messages match tests

---

## Testing Strategy

### Unit Test Coverage

**Per-Component Tests:**

1. **Dodecahedral Projection**
   ```bash
   pytest tests/test_a5.py::TestA5CoordinateTransformations -v
   ```
   - Test forward/reverse roundtrip
   - Test all 12 origins
   - Test edge cases (poles, antimeridian)

2. **Hilbert Curves**
   ```bash
   pytest tests/test_a5.py::TestA5Grid::test_cell_encoding_decoding -v
   ```
   - Test all resolutions 2-10
   - Test S-value roundtrip
   - Test bit width calculation

3. **Segment-Quintant**
   ```bash
   pytest tests/test_a5.py::TestA5Grid::test_pentagon_vertex_generation -v
   ```
   - Test all 12 origins
   - Test all 5 segments per origin
   - Test forward/reverse inverse

4. **Cell Operations**
   ```bash
   pytest tests/test_a5.py::TestA5API -v
   ```
   - Test cell_to_lonlat accuracy
   - Test cell_to_boundary vertex count
   - Test parent/child relationships

### Integration Tests

1. **Roundtrip Accuracy**
   - lonlat → cell_id → lonlat: error < 0.1°
   - Test 1000 random points globally
   - Test all resolutions 0-10

2. **Palmer Compatibility**
   ```bash
   pytest tests/test_a5_compatibility.py -v
   ```
   - All 14 tests must pass
   - Cell IDs must match exactly
   - Boundaries within 0.1° tolerance

3. **Full Suite**
   ```bash
   pytest tests/test_a5.py -v
   ```
   - Must achieve 60/60 passing
   - No Palmer imports in stack traces
   - Run time < 30 seconds

### Validation Tests

Create new test file: `tests/test_a5_native_validation.py`

```python
def test_no_palmer_imports():
    """Verify no Palmer dependencies in implementation."""
    import sys

    # Remove Palmer from modules if present
    if 'a5' in sys.modules:
        del sys.modules['a5']

    # Try to block Palmer import
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == 'a5' or name.startswith('a5.'):
            raise ImportError(f"Palmer import blocked: {name}")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = mock_import

    try:
        # Import our implementation
        from m3s.a5 import lonlat_to_cell, cell_to_lonlat, cell_to_boundary

        # Test basic operations
        cell_id = lonlat_to_cell(-74.0, 40.7, 5)
        lon, lat = cell_to_lonlat(cell_id)
        boundary = cell_to_boundary(cell_id)

        assert cell_id > 0
        assert -180 <= lon <= 180
        assert -90 <= lat <= 90
        assert len(boundary) == 6  # 5 vertices + closing

    finally:
        builtins.__import__ = real_import

def test_accuracy_vs_palmer():
    """Test that our implementation matches Palmer's accuracy."""
    import a5 as palmer_a5
    from m3s.a5 import lonlat_to_cell, cell_to_lonlat

    test_points = [
        (0, 0), (-74, 40), (139, 35), (151, -33),
        (-120, 60), (45, -25), (180, 0), (-180, 0),
    ]

    for lon, lat in test_points:
        for resolution in [0, 1, 2, 3, 5, 7]:
            # Our implementation
            our_cell = lonlat_to_cell(lon, lat, resolution)
            our_lon, our_lat = cell_to_lonlat(our_cell)

            # Palmer's implementation
            palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), resolution)
            palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(palmer_cell)

            # Cell IDs must match exactly
            assert our_cell == palmer_cell, \
                f"Cell ID mismatch at ({lon},{lat}) res={resolution}"

            # Centers should be very close
            lon_error = abs(our_lon - palmer_lon)
            lat_error = abs(our_lat - palmer_lat)

            # Handle antimeridian
            if lon_error > 180:
                lon_error = 360 - lon_error

            assert lon_error < 0.1, \
                f"Lon error {lon_error}° at ({lon},{lat}) res={resolution}"
            assert lat_error < 0.1, \
                f"Lat error {lat_error}° at ({lon},{lat}) res={resolution}"
```

---

## Success Criteria

### Primary Goals

- [ ] **60/60 tests passing** in `tests/test_a5.py`
- [ ] **14/14 tests passing** in `tests/test_a5_compatibility.py`
- [ ] **Zero Palmer imports** in implementation files (`m3s/a5/*.py`)
- [ ] **Roundtrip accuracy** < 0.1° error for all resolutions

### Secondary Goals

- [ ] **Performance**: Native operations within 2x of Palmer's speed
- [ ] **Memory**: No significant memory regression
- [ ] **Documentation**: All new functions documented
- [ ] **Code quality**: Passes `black`, `ruff`, `mypy`

### Validation Criteria

```python
# All must pass
assert test_count_passing == 60
assert test_count_failing == 0
assert palmer_imports_count == 0
assert max_roundtrip_error < 0.1
assert performance_ratio < 2.0
```

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Projection math errors | High | High | Extensive unit tests, compare with Palmer |
| Hilbert scaling issues | Medium | High | Test all resolutions, verify bit widths |
| Pole edge cases | Medium | Medium | Special case handling, extra tests |
| Performance degradation | Low | Low | Profile and optimize hotspots |
| Test suite changes needed | Low | Low | Document any test modifications |

### Implementation Risks

| Risk | Mitigation |
|------|------------|
| Underestimated complexity | Build in 20% time buffer |
| Palmer's algorithm unclear | Study source code, contact maintainer |
| Tests expose new issues | Fix incrementally, don't block on perfect |
| Integration breaks existing code | Git branches, rollback plan |

### Contingency Plans

1. **If projection accuracy fails:**
   - Fall back to using Palmer's dodecahedron projection code (properly attributed)
   - Focus on getting other components native

2. **If Hilbert mapping fails:**
   - Use simpler quadtree subdivision (may change cell IDs)
   - OR use Palmer's Hilbert code (properly attributed)

3. **If time runs out:**
   - Prioritize most-used functions (lonlat_to_cell, cell_to_lonlat)
   - Accept Palmer dependency for boundary/hierarchy
   - Document clearly which functions are native vs Palmer

---

## Timeline

### Detailed Schedule (50 hours total)

**Week 1: Core Projection (24 hours)**
- Monday-Tuesday: Phase 1 - Reverse Projection (20h)
- Wednesday: Phase 2 - Segment Inverse (4h)

**Week 2: Hilbert & Cell Ops (20 hours)**
- Monday: Phase 3 - Hilbert Reverse (8h)
- Tuesday: Phase 4 - cell_to_lonlat (6h)
- Wednesday: Phase 5 - cell_to_boundary (6h)

**Week 3: Hierarchy & Polish (14 hours)**
- Monday: Phase 6 - Cell Hierarchy (8h)
- Tuesday AM: Phase 7 - Pole Cases (4h)
- Tuesday PM: Phase 8 - Attributes/Neighbors (2h)
- Wednesday AM: Phase 9 - Error Handling (2h)
- Wednesday PM: Final testing (2h)

### Daily Checkpoints

**Each Day:**
1. Run relevant test subset
2. Document progress in markdown
3. Commit working code to git
4. Update this plan with findings

**Each Phase:**
1. Run full test suite
2. Update test pass count
3. Profile performance
4. Document any blockers

---

## Deliverables

### Code Deliverables

1. **Updated Files:**
   - `m3s/a5/coordinates.py` - Fixed reverse projection
   - `m3s/a5/hilbert.py` - Fixed reverse Hilbert
   - `m3s/a5/projections/origin_data.py` - Added segment_to_quintant
   - `m3s/a5/cell.py` - Native cell_to_lonlat, cell_to_boundary, get_children
   - `m3s/a5/geometry.py` - Pentagon vertex calculations

2. **New Files:**
   - `tests/test_a5_native_validation.py` - Native implementation validation
   - `docs/a5_native_implementation.md` - Technical documentation

3. **Documentation Updates:**
   - `CLAUDE.md` - Update A5 status to "100% native"
   - `README.md` - Remove Palmer dependency note
   - `requirements.txt` - Remove a5-py

### Test Results

**Final Report Format:**
```
A5 Native Implementation - Test Results
========================================

Test Suite: tests/test_a5.py
  Passing: 60/60 (100%)
  Failing: 0/60 (0%)
  Warnings: 0

Compatibility Suite: tests/test_a5_compatibility.py
  Passing: 14/14 (100%)
  Failing: 0/14 (0%)

Palmer Dependencies:
  Implementation imports: 0
  Test suite imports: 1 (compatibility tests only)

Performance:
  lonlat_to_cell: 15 µs/call (Palmer: 12 µs, ratio: 1.25x)
  cell_to_lonlat: 18 µs/call (Palmer: 14 µs, ratio: 1.29x)
  cell_to_boundary: 45 µs/call (Palmer: 38 µs, ratio: 1.18x)

Accuracy:
  Max roundtrip error: 0.042° (@ resolution 10, lat=85°)
  Mean roundtrip error: 0.008°
  Cell ID match rate: 100%

Status: ✅ ALL SUCCESS CRITERIA MET
```

---

## Appendices

### Appendix A: Key Mathematical References

1. **Gnomonic Projection:**
   - Snyder, J. P. (1987). Map Projections--A Working Manual
   - https://en.wikipedia.org/wiki/Gnomonic_projection

2. **Hilbert Curves:**
   - Hilbert, D. (1891). "Über die stetige Abbildung einer Linie auf ein Flächenstück"
   - https://en.wikipedia.org/wiki/Hilbert_curve

3. **Dodecahedral Grid Systems:**
   - Sahr, K., White, D., & Kimerling, A. J. (2003). "Geodesic Discrete Global Grid Systems"
   - Palmer, F. (2024). "A5 Pentagonal DGGS" - https://github.com/felixpalmer/a5-py

### Appendix B: Palmer Source Code References

Key files to study in felixpalmer/a5-py:
- `a5/core/cell.py` - Cell operations
- `a5/core/dodecahedron.py` - Projection implementation
- `a5/core/hilbert.py` - Hilbert curve
- `a5/core/pentagon.py` - Pentagon geometry

### Appendix C: Debugging Tools

**Visualization Helper:**
```python
def visualize_projection_error(resolution=3):
    """Create heatmap of projection errors."""
    import numpy as np
    import matplotlib.pyplot as plt

    lons = np.linspace(-180, 180, 72)
    lats = np.linspace(-90, 90, 36)

    errors = np.zeros((len(lats), len(lons)))

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            cell_id = lonlat_to_cell(lon, lat, resolution)
            result_lon, result_lat = cell_to_lonlat(cell_id)

            error = np.sqrt((result_lon - lon)**2 + (result_lat - lat)**2)
            errors[i, j] = error

    plt.imshow(errors, extent=[-180, 180, -90, 90], aspect='auto')
    plt.colorbar(label='Error (degrees)')
    plt.title(f'Projection Error Heatmap (Resolution {resolution})')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.show()
```

**Performance Profiler:**
```python
def profile_operations():
    """Profile all major operations."""
    import timeit

    operations = {
        'lonlat_to_cell': lambda: lonlat_to_cell(-74, 40, 5),
        'cell_to_lonlat': lambda: cell_to_lonlat(test_cell_id),
        'cell_to_boundary': lambda: cell_to_boundary(test_cell_id),
        'get_children': lambda: get_children(test_cell_id),
    }

    for name, func in operations.items():
        time = timeit.timeit(func, number=1000) / 1000
        print(f"{name}: {time*1e6:.2f} µs")
```

---

## Final Notes

This plan represents a complete roadmap to native A5 implementation. Key success factors:

1. **Follow phases sequentially** - Each builds on previous
2. **Test incrementally** - Don't wait until the end
3. **Compare with Palmer** - Use as reference, not dependency
4. **Document issues** - Track blockers and solutions
5. **Stay focused** - Don't optimize prematurely

**Expected Outcome:** 60/60 tests passing, zero Palmer dependencies, production-ready A5 grid system fully integrated into M3S.

---

**Document Version:** 1.0
**Last Updated:** 2026-01-25
**Status:** Ready for Implementation
