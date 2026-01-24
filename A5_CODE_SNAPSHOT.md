# A5 Implementation - Code Snapshot

**Purpose:** This file captures the exact state of critical code sections as of January 24, 2026, to aid in resuming work.

---

## Current Origin Generation (WORKING - Don't Change!)

**File:** `m3s/a5/constants.py` (lines ~77-104)

```python
# Generate origins in Palmer's natural order (interleaved rings)
# Palmer's generation loop creates ring 1 and ring 2 origins in pairs
_DODEC_ORIGINS_NATURAL: List[Tuple[float, float]] = [(NORTH_POLE_THETA, NORTH_POLE_PHI)]

# Middle band: interleave ring 1 and ring 2
PI_OVER_5 = math.pi / 5
for i in range(5):
    alpha = i * 2 * math.pi / 5  # Ring 1 theta
    alpha2 = alpha + PI_OVER_5  # Ring 2 theta (offset by 36°)

    # Add ring 1 origin
    _DODEC_ORIGINS_NATURAL.append((alpha, RING1_PHI))

    # Add ring 2 origin
    _DODEC_ORIGINS_NATURAL.append((alpha2, RING2_PHI))

# South pole
_DODEC_ORIGINS_NATURAL.append((SOUTH_POLE_THETA, SOUTH_POLE_PHI))

# Hilbert curve placement order (from Palmer's origin.py)
_ORIGIN_ORDER = [0, 1, 2, 4, 3, 5, 7, 8, 6, 11, 10, 9]

# Reorder origins according to Hilbert curve placement
DODEC_ORIGINS: List[Tuple[float, float]] = [
    _DODEC_ORIGINS_NATURAL[old_id] for old_id in _ORIGIN_ORDER
]

# QUINTANT_FIRST after reordering
QUINTANT_FIRST: List[int] = [
    _QUINTANT_FIRST_NATURAL[old_id] for old_id in _ORIGIN_ORDER
]
```

**Result:** Origins match Palmer's exactly after reordering. ✓

---

## Current Haversine Implementation (WORKING - Don't Change!)

**File:** `m3s/a5/geometry.py` (lines ~302-336)

```python
def _haversine(
    self, point: Tuple[float, float], axis: Tuple[float, float]
) -> float:
    """
    Modified haversine formula to calculate great-circle distance.

    Returns the "angle" parameter (not the full arc distance), which is
    sufficient for comparing distances. This matches Palmer's implementation.
    """
    theta, phi = point
    theta2, phi2 = axis

    dtheta = theta2 - theta
    dphi = phi2 - phi

    a1 = math.sin(dphi / 2)
    a2 = math.sin(dtheta / 2)

    # Return 'a' parameter directly (not full haversine)
    # This is faster and sufficient for distance comparison
    angle = a1 * a1 + a2 * a2 * math.sin(phi) * math.sin(phi2)

    return angle
```

**Result:** Origin finding matches Palmer's exactly. ✓

---

## Current Authalic Projection (WORKING - Don't Change!)

**File:** `m3s/a5/coordinates.py` (lines ~63-135)

```python
@staticmethod
def _apply_authalic_coefficients(phi: float, coefficients: tuple) -> float:
    """Apply authalic projection coefficients using Clenshaw summation."""
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    X = 2 * (cos_phi - sin_phi) * (cos_phi + sin_phi)  # = cos(2*phi)

    # Clenshaw summation (order 6)
    C0, C1, C2, C3, C4, C5 = coefficients

    B6 = 0.0
    B5 = C5
    B4 = X * B5 + C4
    B3 = X * B4 - B5 + C3
    B2 = X * B3 - B4 + C2
    B1 = X * B2 - B3 + C1
    B0 = X * B1 - B2 + C0

    return phi + math.sin(2 * phi) * B0

@staticmethod
def lonlat_to_spherical(lon: float, lat: float) -> Tuple[float, float]:
    """Convert longitude/latitude to spherical coordinates."""
    # Apply longitude offset
    theta = math.radians(lon) + LONGITUDE_OFFSET
    theta = theta % (2 * math.pi)
    if theta < 0:
        theta += 2 * math.pi

    # Convert latitude to radians
    geodetic_lat_rad = math.radians(lat)

    # Apply authalic (equal-area) projection
    authalic_lat_rad = CoordinateTransformer.geodetic_to_authalic(geodetic_lat_rad)

    # Convert to polar angle
    phi = math.pi / 2 - authalic_lat_rad

    return theta, phi
```

**Result:** Coordinate transformation matches Palmer's. ✓

---

## Current Serialization (WORKING - Don't Change!)

**File:** `m3s/a5/serialization.py` (lines ~48-124)

```python
@staticmethod
def encode(origin: int, segment: int, s: int, resolution: int) -> int:
    """Encode to 64-bit cell ID (Palmer's specification)."""
    # Calculate resolution marker position
    if resolution < FIRST_HILBERT_RESOLUTION:
        R = resolution + 1
    else:
        hilbert_resolution = 1 + resolution - FIRST_HILBERT_RESOLUTION
        R = 2 * hilbert_resolution + 1

    # Normalize segment using first_quintant offset
    first_quintant = QUINTANT_FIRST[origin]
    segment_n = (segment - first_quintant + 5) % 5

    # Encode top 6 bits
    if resolution == 0:
        index = origin << HILBERT_START_BIT
    else:
        index = (5 * origin + segment_n) << HILBERT_START_BIT

    # For Hilbert resolutions, add S value
    if resolution >= FIRST_HILBERT_RESOLUTION:
        hilbert_levels = resolution - FIRST_HILBERT_RESOLUTION + 1
        hilbert_bits = 2 * hilbert_levels
        index += s << (HILBERT_START_BIT - hilbert_bits)

    # Resolution marker
    index |= 1 << (HILBERT_START_BIT - R)

    return index
```

**Result:** Cell ID encoding matches Palmer's for resolution 0. ✓

---

## PROBLEM AREA: Face Projection (NEEDS FIXING!)

**File:** `m3s/a5/coordinates.py` (lines ~240-295)

```python
@staticmethod
def cartesian_to_face_ij(
    xyz: np.ndarray, origin_xyz: np.ndarray
) -> Tuple[float, float]:
    """
    Project 3D Cartesian point to 2D face IJ coordinates.

    ⚠️ THIS IS THE PROBLEM AREA ⚠️
    Currently uses simple gnomonic projection.
    Palmer uses polyhedral projection with quaternions.
    """
    # Normalize both vectors
    point = xyz / np.linalg.norm(xyz)
    face_normal = origin_xyz / np.linalg.norm(origin_xyz)

    # Simple gnomonic projection (WRONG FOR RESOLUTION 1+)
    cos_angle = np.dot(point, face_normal)
    if abs(cos_angle) < EPSILON:
        return 0.0, 0.0

    scale = 1.0 / cos_angle
    projected = point * scale
    offset = projected - face_normal

    # Create local coordinate system (SIMPLIFIED - NOT LIKE PALMER)
    if abs(face_normal[2]) < 0.9:
        up = np.array([0, 0, 1])
    else:
        up = np.array([1, 0, 0])

    basis_i = np.cross(face_normal, up)
    basis_i = basis_i / np.linalg.norm(basis_i)

    basis_j = np.cross(face_normal, basis_i)
    basis_j = basis_j / np.linalg.norm(basis_j)

    # Project onto basis (PRODUCES DIFFERENT IJ THAN PALMER)
    i = np.dot(offset, basis_i)
    j = np.dot(offset, basis_j)

    return i, j
```

**What Palmer Does Instead:**

```python
# Palmer's approach (from C:\Users\nicar\git\m3s\a5-py\a5\projections\dodecahedron.py):
def forward(self, spherical: Spherical, origin_id: int) -> Face:
    """Projects spherical to face using polyhedral projection."""
    origin = origins[origin_id]

    # 1. Transform to Cartesian
    unprojected = to_cartesian(spherical)

    # 2. Apply quaternion rotation to origin space
    out = vec3.transformQuat(unprojected, origin.inverse_quat)

    # 3. Project gnomonically to polar
    projected_spherical = to_spherical(out)
    polar = self.gnomonic.forward(projected_spherical)

    # 4. Rotate around face axis
    rho, gamma = polar
    polar = (rho, gamma - origin.angle)

    # 5. Get face triangle and use polyhedral projection
    face_triangle_index = self.get_face_triangle_index(polar)
    reflect = self.should_reflect(polar)
    face_triangle = self.get_face_triangle(face_triangle_index, reflect, False)
    spherical_triangle = self.get_spherical_triangle(face_triangle_index, origin_id, reflect)

    # 6. Return face coordinates using barycentric transformation
    return self.polyhedral.forward(unprojected, spherical_triangle, face_triangle)
```

**Key Differences:**
1. Palmer uses **quaternion rotation** to transform into origin's local space
2. Palmer uses **face triangles** (10 per pentagon face)
3. Palmer uses **barycentric coordinates** for proper projection
4. Palmer handles **edge reflection** cases

---

## Current Cell Operations (Uses Broken Projection)

**File:** `m3s/a5/cell.py` (lines ~75-102)

```python
def lonlat_to_cell(self, lon: float, lat: float, resolution: int) -> int:
    """Convert geographic coordinates to A5 cell ID."""
    validate_longitude(lon)
    validate_latitude(lat)
    validate_resolution(resolution)

    # Step 1: Convert to spherical
    theta, phi = self.transformer.lonlat_to_spherical(lon, lat)

    # Step 2: Find nearest origin (✓ WORKS CORRECTLY)
    origin_id = self.dodec.find_nearest_origin((theta, phi))

    # Step 3: Convert to Cartesian for projection
    xyz = self.transformer.spherical_to_cartesian(theta, phi)
    origin_xyz = self.dodec.get_origin_cartesian(origin_id)

    # Step 4: Project to face IJ (✗ WRONG METHOD)
    i, j = self.transformer.cartesian_to_face_ij(xyz, origin_xyz)

    # Step 5: Determine segment (✗ WRONG BECAUSE IJ IS WRONG)
    segment = self.transformer.determine_quintant(i, j)

    # Step 6: Encode cell ID
    if resolution >= 2:
        raise NotImplementedError("Phase 3")

    s = 0
    cell_id = self.serializer.encode(origin_id, segment, s, resolution)

    return cell_id
```

**What Needs to Change:**
- Replace `cartesian_to_face_ij()` call with Palmer's polyhedral projection
- This requires implementing quaternion math, face triangles, and barycentric coordinates

---

## Test Results Snapshot

**Resolution 0 Tests (5/5 passing ✓):**
```bash
$ pytest tests/test_a5_compatibility.py::TestCellIDCompatibility::test_cell_id_resolution_0_* -v

test_cell_id_resolution_0_nyc PASSED
test_cell_id_resolution_0_london PASSED
test_cell_id_resolution_0_equator PASSED
test_cell_id_resolution_0_north_pole PASSED
test_cell_id_resolution_0_south_pole PASSED
```

**Resolution 1 Tests (0/3 passing ✗):**
```bash
$ pytest tests/test_a5_compatibility.py::TestCellIDCompatibility::test_cell_id_resolution_1_* -v

test_cell_id_resolution_1_nyc FAILED
  AssertionError: Cell ID mismatch at NYC res 1:
  ours=0x1900000000000000, Palmer's=0x2500000000000000
  (origin match: 1=1 ✓, segment mismatch: 3≠1 ✗)

test_cell_id_resolution_1_london FAILED
  AssertionError: Cell ID mismatch at London res 1:
  ours=0x5500000000000000, Palmer's=0x6100000000000000
  (origin match: 4=4 ✓, segment mismatch: 3≠4 ✗)

test_cell_id_resolution_1_global_coverage FAILED
  (Multiple mismatches globally)
```

---

## Palmer's Required Components

### 1. Quaternion Math (from C:\Users\nicar\git\m3s\a5-py\a5\math\quat.py)

**Key functions needed:**
- `create()` - Create identity quaternion
- `conjugate(out, quat)` - Conjugate for inverse rotation
- `transformVec3(out, vec, quat)` - Apply quaternion to vector

**Palmer's quaternion storage:**
```python
# In origin.py, each origin has:
class Origin:
    quat: Tuple[float, float, float, float]  # Rotation quaternion
    inverse_quat: Tuple[float, float, float, float]  # Conjugate for inverse
```

### 2. Pentagon BASIS Matrices (from C:\Users\nicar\git\m3s\a5-py\a5\core\pentagon.py)

```python
# These matrices transform between face coordinates and IJ coordinates
BASIS = ((a, b), (c, d))  # Actual values in Palmer's code
BASIS_INVERSE = ((e, f), (g, h))  # Actual values in Palmer's code

# Used like:
def face_to_ij(face: Face) -> IJ:
    basis_flat = [BASIS_INVERSE[0][0], BASIS_INVERSE[1][0],
                  BASIS_INVERSE[0][1], BASIS_INVERSE[1][1]]
    return vec2.transformMat2(face, basis_flat)
```

### 3. Face Triangles (from C:\Users\nicar\git\m3s\a5-py\a5\projections\dodecahedron.py)

Each pentagonal face is divided into 10 triangles for barycentric projection.

---

## Files That Need Creating

```bash
m3s/a5/projections/
├── __init__.py                # Package init
├── quaternion.py              # Quaternion math (port from Palmer)
├── pentagon.py                # BASIS matrices (port from Palmer)
├── polyhedral.py              # Barycentric transformation (port from Palmer)
├── gnomonic.py                # Gnomonic projection (exists in Palmer)
└── dodecahedron.py            # Main projection class (port from Palmer)
```

---

## Summary

**Works Perfectly (Don't Touch):**
1. Origin generation and ordering ✓
2. Haversine distance calculation ✓
3. Authalic projection ✓
4. Cell ID serialization (res 0) ✓
5. Resolution 0 cell operations ✓

**Broken (Needs Fixing):**
1. Face IJ projection (`cartesian_to_face_ij` in coordinates.py) ✗
2. Segment determination (depends on above) ✗
3. Resolution 1+ cell operations ✗

**Fix Required:**
- Implement polyhedral projection with quaternions
- Replace gnomonic with Palmer's projection method
- This will make resolution 1 tests pass

**Then Next:**
- Implement Hilbert curves (Phase 3)
- Add resolution 2+ support

---

**Snapshot Date:** January 24, 2026
**Code State:** Working for Resolution 0, Needs polyhedral projection for Resolution 1+
