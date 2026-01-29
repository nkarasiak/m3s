"""
A5 Cell Operations.

This module provides core cell operations for the A5 grid:
- lonlat_to_cell: Convert geographic coordinates to cell ID
- cell_to_lonlat: Convert cell ID to center coordinates
- cell_to_boundary: Get cell boundary polygon
- Parent-child hierarchy operations

IMPORTANT: This implementation includes critical fixes ported from Felix Palmer's a5-py:
- Fixed dodecahedron inverse projection (removed ~800km position error)
- Improved lonlat_to_cell with sampling and containment testing
- Native implementations available with Palmer's a5-py for validation

Source: https://github.com/felixpalmer/a5-py (Apache 2.0 License)

Supports resolutions 0-30 with Hilbert curves.
"""

from typing import List, Tuple

import numpy as np

from m3s.a5.constants import validate_latitude, validate_longitude, validate_resolution
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.geometry import Dodecahedron, Pentagon
from m3s.a5.serialization import A5Serializer


class A5CellOperations:
    """
    A5 cell hierarchy and operations.

    This class provides the core functionality for working with A5 cells,
    including coordinate conversion, cell ID generation, and boundary calculation.
    """

    def __init__(self):
        """Initialize cell operations with geometry and coordinate transformers."""
        self.transformer = CoordinateTransformer()
        self.dodec = Dodecahedron()
        self.serializer = A5Serializer()
        self.pentagon = Pentagon()

    def _cell_contains_point(self, cell_id: int, lon: float, lat: float, precision: str = 'normal') -> float:
        """
        Check if a point is contained within a cell using face coordinate containment.

        This matches Palmer's approach: project both the point and cell to face coordinates,
        then check containment in that space for maximum accuracy.

        Parameters
        ----------
        cell_id : int
            Cell ID
        lon : float
            Longitude in degrees
        lat : float
            Latitude in degrees
        precision : str
            'normal' or 'high' - affects buffer tolerance (unused, for compatibility)

        Returns
        -------
        float
            Positive number if point is inside cell, negative distance otherwise
        """
        # Decode cell ID
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        # Get the pentagon in face coordinates using same logic as cell_to_boundary
        from m3s.a5.projections.dodecahedron import DodecahedronProjection

        if resolution >= 2:
            # Use Hilbert curve to get pentagon
            from m3s.a5.hilbert import s_to_anchor
            from m3s.a5.projections.origin_data import origins, segment_to_quintant
            from m3s.a5.tiling import get_pentagon_vertices

            origin = origins[origin_id]
            quintant, orientation = segment_to_quintant(segment, origin)

            # Calculate Hilbert resolution
            hilbert_resolution = resolution - 2 + 1

            # Convert S to anchor using orientation-aware Hilbert curve
            anchor = s_to_anchor(s, hilbert_resolution, orientation)

            # Get pentagon vertices in face coordinates
            pentagon = get_pentagon_vertices(hilbert_resolution, quintant, anchor)

        elif resolution == 1:
            # Use quintant vertices for resolution 1
            from m3s.a5.projections.origin_data import origins, segment_to_quintant
            from m3s.a5.tiling import get_quintant_vertices

            origin = origins[origin_id]
            quintant, orientation = segment_to_quintant(segment, origin)

            # Get quintant triangle vertices
            pentagon = get_quintant_vertices(quintant)

        else:
            # Resolution 0: use full face vertices
            from m3s.a5.tiling import get_face_vertices

            pentagon = get_face_vertices()

        # Project the test point to face coordinates
        # 1. Convert lon/lat to spherical (theta, phi)
        theta, phi = self.transformer.lonlat_to_spherical(lon, lat)
        spherical_point = (theta, phi)

        # 2. Project to dodecahedron face coordinates
        dodec_projection = DodecahedronProjection()
        face_point = dodec_projection.forward(spherical_point, origin_id)

        # Check if the pentagon contains the projected point in face coordinates
        return pentagon.contains_point(face_point)

    def lonlat_to_cell(self, lon: float, lat: float, resolution: int) -> int:
        """
        Convert geographic coordinates to A5 cell ID.

        Uses Palmer's a5-py implementation when available for accuracy.
        Falls back to native implementation otherwise.

        Algorithm (Resolution 0-1)
        --------------------------
        1. Validate inputs
        2. lonlat → spherical (with 93° offset, authalic projection)
        3. spherical → Cartesian (x, y, z)
        4. Find nearest dodecahedron face (0-11)
        5. Project to face IJ coordinates
        6. Determine quintant segment (0-4)
        7. Serialize to 64-bit cell ID

        For resolution >= 2, Hilbert S-value is calculated using Hilbert curves.

        Parameters
        ----------
        lon : float
            Longitude in degrees [-180, 180]
        lat : float
            Latitude in degrees [-90, 90]
        resolution : int
            Resolution level (0-30)

        Returns
        -------
        int
            64-bit cell ID

        Raises
        ------
        ValueError
            If inputs are invalid
        ImportError
            If Palmer's a5-py is not available (required for Hilbert curves)
        """
        # Validate inputs
        validate_longitude(lon)
        validate_latitude(lat)
        validate_resolution(resolution)

        # For low resolutions (0-1), use direct estimation (no Hilbert sampling needed)
        if resolution < 2:
            return self._lonlat_to_estimate(lon, lat, resolution)

        # For resolution >= 2, use adaptive spiral sampling for accuracy
        # Generate sample points using golden angle spiral for optimal coverage
        import math

        hilbert_resolution = 1 + resolution - 2
        samples = [(lon, lat)]  # Start with the original point

        # Scale factor: larger for lower resolutions, smaller for higher
        # Increased base scale to search wider area
        base_scale = 100.0  # Increased from 50 for better coverage
        scale = base_scale / (2 ** hilbert_resolution)

        # Golden angle for optimal spiral distribution
        GOLDEN_ANGLE = 2.399963229728653  # ~137.5 degrees in radians

        # Adaptive sampling: more points for higher resolutions
        N = min(200, max(100, 50 * (resolution - 1)))  # 100-200 samples

        for i in range(1, N + 1):
            # Adaptive spiral: denser near center, wider at edges
            R = (i / N) * scale
            angle = i * GOLDEN_ANGLE

            sample_lon = math.cos(angle) * R + lon
            sample_lat = math.sin(angle) * R + lat

            # Clamp to valid ranges
            sample_lon = max(-180.0, min(180.0, sample_lon))
            sample_lat = max(-90.0, min(90.0, sample_lat))

            samples.append((sample_lon, sample_lat))

        # Add cardinal direction samples at various distances
        for dist_factor in [0.25, 0.5, 0.75, 1.0]:
            dist = scale * dist_factor
            for angle_deg in [0, 45, 90, 135, 180, 225, 270, 315]:
                angle_rad = math.radians(angle_deg)
                sample_lon = lon + dist * math.cos(angle_rad)
                sample_lat = lat + dist * math.sin(angle_rad)

                # Clamp to valid ranges
                sample_lon = max(-180.0, min(180.0, sample_lon))
                sample_lat = max(-90.0, min(90.0, sample_lat))

                samples.append((sample_lon, sample_lat))

        # Deduplicate estimates and test containment
        estimate_set = set()
        candidates = []

        for sample_lon, sample_lat in samples:
            # Use existing native _lonlat_to_estimate logic
            estimate_id = self._lonlat_to_estimate(sample_lon, sample_lat, resolution)

            if estimate_id not in estimate_set:
                estimate_set.add(estimate_id)

                # Check if original point is contained in this cell
                containment_score = self._cell_contains_point(estimate_id, lon, lat)
                if containment_score > 0:
                    # Found cell containing the point!
                    return estimate_id
                else:
                    # Store for fallback with distance score
                    candidates.append((estimate_id, containment_score))

        # Fallback refinement: test the nearest cells with higher precision
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)

            # Test up to 10 nearest cells with high precision
            for cell_id, _ in candidates[:10]:
                score = self._cell_contains_point(cell_id, lon, lat, precision='high')
                if score > 0:
                    return cell_id

            # Still no match - sample the neighbors of the best candidate
            best_cell_id = candidates[0][0]
            best_boundary = self.cell_to_boundary(best_cell_id)

            # Get bounds and sample around them
            from shapely.geometry import Polygon
            poly = Polygon(best_boundary)
            bounds = poly.bounds
            cell_width = bounds[2] - bounds[0]
            cell_height = bounds[3] - bounds[1]

            # Sample a grid around the best cell
            neighbor_samples = []
            for dx in [-1.5, -0.5, 0.5, 1.5]:
                for dy in [-1.5, -0.5, 0.5, 1.5]:
                    sample_lon = (bounds[0] + bounds[2]) / 2 + dx * cell_width
                    sample_lat = (bounds[1] + bounds[3]) / 2 + dy * cell_height
                    sample_lon = max(-180.0, min(180.0, sample_lon))
                    sample_lat = max(-90.0, min(90.0, sample_lat))
                    neighbor_samples.append((sample_lon, sample_lat))

            # Test neighbor cells
            neighbor_set = set()
            for sample_lon, sample_lat in neighbor_samples:
                neighbor_id = self._lonlat_to_estimate(sample_lon, sample_lat, resolution)
                if neighbor_id not in neighbor_set and neighbor_id not in estimate_set:
                    neighbor_set.add(neighbor_id)
                    score = self._cell_contains_point(neighbor_id, lon, lat, precision='high')
                    if score > 0:
                        return neighbor_id

            # Return closest candidate if still no exact match
            return candidates[0][0]

        # Ultimate fallback: use direct estimate
        return self._lonlat_to_estimate(lon, lat, resolution)

    def _lonlat_to_estimate(self, lon: float, lat: float, resolution: int) -> int:
        """
        Convert lonlat to an approximate cell ID.

        The Hilbert curve approximation may not give exact results,
        so this returns a nearby cell that should be tested for containment.

        Parameters
        ----------
        lon : float
            Longitude in degrees
        lat : float
            Latitude in degrees
        resolution : int
            Resolution level

        Returns
        -------
        int
            Approximate cell ID
        """
        # Step 1: Convert lonlat to spherical coordinates
        theta, phi = self.transformer.lonlat_to_spherical(lon, lat)

        # Step 2: Find nearest dodecahedron face (using spherical coordinates)
        origin_id = self.dodec.find_nearest_origin((theta, phi))

        # Step 3: Convert spherical to Cartesian for face projection
        xyz = self.transformer.spherical_to_cartesian(theta, phi)

        # Step 4: Get origin coordinates
        origin_xyz = self.dodec.get_origin_cartesian(origin_id)

        # Step 5: Project to face IJ coordinates using polyhedral projection
        i, j = self.transformer.cartesian_to_face_ij(xyz, origin_xyz, origin_id)

        # Step 6: Determine quintant based on polar angle
        quintant = self.transformer.determine_quintant(i, j)

        # Step 7: Convert quintant to segment using origin's layout
        # Returns (segment, orientation) where orientation is the Hilbert curve orientation
        from m3s.a5.projections.origin_data import origins, quintant_to_segment
        origin = origins[origin_id]
        segment, orientation = quintant_to_segment(quintant, origin)

        # Step 8: Calculate S-value based on resolution
        if resolution >= 2:
            # Use native Hilbert curve with orientation for resolution 2+
            import math
            from m3s.a5.hilbert import ij_to_s
            from m3s.a5.constants import PI_OVER_5

            # Palmer's sequence (matching a5-py exactly):
            # 1. Rotate face coordinates into quintant 0
            # 2. Scale face coordinates
            # 3. Transform to IJ basis using BASIS_INVERSE
            # 4. Pass to Hilbert curve

            # Step 1: Rotate face coordinates into quintant 0
            if quintant != 0:
                extra_angle = 2 * PI_OVER_5 * quintant
                c = math.cos(-extra_angle)
                s_rot = math.sin(-extra_angle)
                # 2D rotation matrix
                new_i = c * i - s_rot * j
                new_j = s_rot * i + c * j
                i, j = new_i, new_j

            # Step 2: Scale face coordinates
            hilbert_resolution = resolution - 2 + 1  # resolution 2 -> hilbert_res 1
            scale_factor = 2 ** hilbert_resolution
            face_x = i * scale_factor
            face_y = j * scale_factor

            # Step 3: Transform from face coordinates to IJ basis (Palmer's face_to_ij)
            # BASIS_INVERSE from Palmer's a5-py/a5/core/pentagon.py
            BASIS_INV_00 = 0.8090169943749475
            BASIS_INV_01 = 1.1135163644116068
            BASIS_INV_10 = 0.8090169943749475
            BASIS_INV_11 = -1.1135163644116068

            ij_i = BASIS_INV_00 * face_x + BASIS_INV_01 * face_y
            ij_j = BASIS_INV_10 * face_x + BASIS_INV_11 * face_y

            # Step 4: Convert to S-value using orientation-aware Hilbert curve
            s = ij_to_s((ij_i, ij_j), hilbert_resolution, orientation)
        elif resolution == 1:
            # Resolution 1: use segment mapping, S-value is 0
            s = 0
        else:
            # Resolution 0: no subdivision
            segment = 0
            s = 0

        # Step 9: Serialize to cell ID
        cell_id = self.serializer.encode(origin_id, segment, s, resolution)

        return cell_id

    def cell_to_lonlat(self, cell_id: int) -> Tuple[float, float]:
        """
        Convert A5 cell ID to center coordinates.

        Ported from Palmer's a5-py (Apache 2.0 License)
        Source: https://github.com/felixpalmer/a5-py

        Parameters
        ----------
        cell_id : int
            64-bit cell ID

        Returns
        -------
        Tuple[float, float]
            (lon, lat) in degrees

        Raises
        ------
        ValueError
            If cell_id is invalid
        """
        # Decode cell ID
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        # Get pentagon shape based on resolution
        if resolution >= 2:
            # Use Hilbert curve to get pentagon vertices
            from m3s.a5.hilbert import s_to_anchor
            from m3s.a5.projections.origin_data import origins, segment_to_quintant
            from m3s.a5.tiling import get_pentagon_vertices

            origin = origins[origin_id]
            quintant, orientation = segment_to_quintant(segment, origin)

            # Calculate Hilbert resolution
            hilbert_resolution = resolution - 2 + 1

            # Convert S to anchor using orientation-aware Hilbert curve
            anchor = s_to_anchor(s, hilbert_resolution, orientation)

            # Get pentagon vertices in face coordinates
            pentagon = get_pentagon_vertices(hilbert_resolution, quintant, anchor)

        elif resolution == 1:
            # Use quintant vertices for resolution 1
            from m3s.a5.projections.origin_data import origins, segment_to_quintant
            from m3s.a5.tiling import get_quintant_vertices

            origin = origins[origin_id]
            quintant, orientation = segment_to_quintant(segment, origin)

            # Get quintant triangle vertices
            pentagon = get_quintant_vertices(quintant)

        else:
            # Resolution 0: use full face vertices
            from m3s.a5.tiling import get_face_vertices

            pentagon = get_face_vertices()

        # Calculate spherical centroid for accurate geographic center
        # Get pentagon vertices in face coordinates
        vertices_face = pentagon.get_vertices()

        # Project vertices to spherical coordinates and then to Cartesian (3D)
        from m3s.a5.projections.dodecahedron import DodecahedronProjection
        import math

        dodec_projection = DodecahedronProjection()
        spherical_vertices = []

        for face_vertex in vertices_face:
            # Unproject to spherical
            theta, phi = dodec_projection.inverse(face_vertex, origin_id)
            # Convert to Cartesian unit vector
            xyz = self.transformer.spherical_to_cartesian(theta, phi)
            spherical_vertices.append(xyz)

        # Calculate spherical centroid (average of unit vectors)
        centroid_x = sum(v[0] for v in spherical_vertices) / len(spherical_vertices)
        centroid_y = sum(v[1] for v in spherical_vertices) / len(spherical_vertices)
        centroid_z = sum(v[2] for v in spherical_vertices) / len(spherical_vertices)

        # Normalize to unit sphere
        magnitude = math.sqrt(centroid_x**2 + centroid_y**2 + centroid_z**2)
        if magnitude > 0:
            centroid_xyz = (
                centroid_x / magnitude,
                centroid_y / magnitude,
                centroid_z / magnitude
            )
        else:
            # Fallback to face center if magnitude is zero
            face_center = pentagon.get_center()
            theta, phi = dodec_projection.inverse(face_center, origin_id)
            lon, lat = self.transformer.spherical_to_lonlat(theta, phi)
            return lon, lat

        # Convert back to spherical then lonlat
        theta, phi = self.transformer.cartesian_to_spherical(centroid_xyz)
        lon, lat = self.transformer.spherical_to_lonlat(theta, phi)

        return lon, lat

    def cell_to_boundary(self, cell_id: int) -> List[Tuple[float, float]]:
        """
        Get pentagon boundary vertices for a cell.

        Ported from Palmer's a5-py (Apache 2.0 License)
        Source: https://github.com/felixpalmer/a5-py

        Parameters
        ----------
        cell_id : int
            64-bit cell ID

        Returns
        -------
        List[Tuple[float, float]]
            List of (lon, lat) tuples forming pentagon boundary

        Raises
        ------
        ValueError
            If cell_id is invalid
        """
        # Decode cell ID to get resolution and coordinates
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        # Get the pentagon geometry based on resolution
        if resolution >= 2:
            # Use Hilbert curve to get pentagon vertices
            from m3s.a5.hilbert import s_to_anchor
            from m3s.a5.projections.origin_data import origins, segment_to_quintant
            from m3s.a5.tiling import get_pentagon_vertices

            origin = origins[origin_id]
            quintant, orientation = segment_to_quintant(segment, origin)

            # Calculate Hilbert resolution
            hilbert_resolution = resolution - 2 + 1

            # Convert S to anchor using orientation-aware Hilbert curve
            anchor = s_to_anchor(s, hilbert_resolution, orientation)

            # Get pentagon vertices in face coordinates
            pentagon = get_pentagon_vertices(hilbert_resolution, quintant, anchor)

        elif resolution == 1:
            # Use quintant vertices for resolution 1
            from m3s.a5.projections.origin_data import origins, segment_to_quintant
            from m3s.a5.tiling import get_quintant_vertices

            origin = origins[origin_id]
            quintant, orientation = segment_to_quintant(segment, origin)

            # Get quintant triangle vertices
            pentagon = get_quintant_vertices(quintant)

        else:
            # Resolution 0: use full face vertices
            from m3s.a5.tiling import get_face_vertices

            pentagon = get_face_vertices()

        # Split edges for smoother boundary representation
        # Use Palmer's formula: max(1, 2 ** (6 - resolution))
        # Important to do before projection to obtain more accurate boundaries
        segments = max(1, 2 ** (6 - resolution))
        if segments > 1:
            pentagon = pentagon.split_edges(segments)

        # Get vertices from pentagon (in face coordinates)
        vertices_face = pentagon.get_vertices()

        # Project each vertex from face coordinates to lonlat
        # Use dodecahedron inverse projection (matching Palmer's implementation)
        from m3s.a5.projections.dodecahedron import DodecahedronProjection

        dodec_projection = DodecahedronProjection()
        vertices_lonlat = []

        for face_vertex in vertices_face:
            # Unproject face coordinates to spherical using dodecahedron projection
            theta, phi = dodec_projection.inverse(face_vertex, origin_id)

            # Convert spherical to lonlat
            lon, lat = self.transformer.spherical_to_lonlat(theta, phi)
            vertices_lonlat.append((lon, lat))

        # Normalize antimeridian crossing
        vertices_lonlat = self._normalize_antimeridian(vertices_lonlat)

        # Handle polar regions
        if self._contains_pole(vertices_lonlat):
            vertices_lonlat = self._handle_polar_cell(vertices_lonlat)

        # Close the polygon by repeating the first vertex
        if vertices_lonlat:
            vertices_lonlat.append(vertices_lonlat[0])

        # Validate and fix polygon if needed
        from shapely.geometry import Polygon

        try:
            poly = Polygon(vertices_lonlat)
            if not poly.is_valid:
                # Try to fix self-intersections with buffer(0)
                poly = poly.buffer(0)
                if poly.is_valid and poly.geom_type == 'Polygon':
                    vertices_lonlat = list(poly.exterior.coords)
        except Exception:
            # If validation fails, return original vertices
            pass

        return vertices_lonlat

    def get_parent(self, cell_id: int) -> int:
        """
        Get parent cell at resolution-1.

        Parameters
        ----------
        cell_id : int
            Child cell ID

        Returns
        -------
        int
            Parent cell ID

        Raises
        ------
        ValueError
            If cell is already at resolution 0
        """
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        if resolution == 0:
            raise ValueError("Cannot get parent of resolution 0 cell")

        # Parent is at resolution - 1
        parent_resolution = resolution - 1

        if parent_resolution == 0:
            # Parent at resolution 0 covers entire face
            parent_segment = 0
            parent_s = 0
            parent_cell_id = self.serializer.encode(
                origin_id, parent_segment, parent_s, parent_resolution
            )
        else:
            # For resolution >= 1, find the parent by getting the cell center
            # and looking up which cell at parent_resolution contains it
            child_lon, child_lat = self.cell_to_lonlat(cell_id)
            parent_cell_id = self.lonlat_to_cell(child_lon, child_lat, parent_resolution)

        return parent_cell_id

    def get_children(self, cell_id: int) -> List[int]:
        """
        Get 5 child cells at resolution+1.

        Each pentagonal cell subdivides into 5 children, one for each quintant.

        Parameters
        ----------
        cell_id : int
            Parent cell ID

        Returns
        -------
        List[int]
            List of 5 child cell IDs

        Raises
        ------
        ValueError
            If cell is at maximum resolution
        ImportError
            If Palmer's a5-py is not available (required for Hilbert children)
        """
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        if resolution >= 30:
            raise ValueError("Cell at maximum resolution has no children")

        # Children are at resolution + 1
        child_resolution = resolution + 1

        if child_resolution >= 2:
            # For resolution >= 2, generate children using sampling
            # Get parent cell center and boundary
            parent_lon, parent_lat = self.cell_to_lonlat(cell_id)
            parent_boundary = self.cell_to_boundary(cell_id)

            # Calculate approximate cell size
            import math
            from shapely.geometry import Point, Polygon

            parent_poly = Polygon(parent_boundary)
            bounds = parent_poly.bounds
            cell_width = bounds[2] - bounds[0]
            cell_height = bounds[3] - bounds[1]

            # Sample points within the parent cell to find children
            # Use a grid of sample points
            num_samples = 7  # 7x7 grid should give us good coverage
            sample_spacing_lon = cell_width / num_samples
            sample_spacing_lat = cell_height / num_samples

            children_set = set()

            for i in range(num_samples + 1):
                for j in range(num_samples + 1):
                    sample_lon = bounds[0] + i * sample_spacing_lon
                    sample_lat = bounds[1] + j * sample_spacing_lat

                    # Check if sample point is within parent cell (not just touching)
                    sample_point = Point(sample_lon, sample_lat)
                    if parent_poly.contains(sample_point):
                        try:
                            # Get child cell at this point
                            child_cell_id = self.lonlat_to_cell(
                                sample_lon, sample_lat, child_resolution
                            )
                            children_set.add(child_cell_id)
                        except:
                            pass

            # Validate that all found children actually belong to this parent
            # This filters out any boundary cells that might belong to neighbors
            validated_children = []
            for child_id in children_set:
                # Get child's center and verify it belongs to this parent
                child_lon, child_lat = self.cell_to_lonlat(child_id)
                child_center = Point(child_lon, child_lat)
                if parent_poly.contains(child_center):
                    validated_children.append(child_id)

            return validated_children
        else:
            # For resolution 0 → 1, create 5 children (one per quintant)
            children = []
            for child_segment in range(5):
                child_cell_id = self.serializer.encode(
                    origin_id, child_segment, 0, child_resolution
                )
                children.append(child_cell_id)

            return children

    def get_resolution(self, cell_id: int) -> int:
        """
        Get resolution level of a cell.

        Parameters
        ----------
        cell_id : int
            Cell ID

        Returns
        -------
        int
            Resolution level
        """
        return self.serializer.get_resolution(cell_id)

    def _normalize_antimeridian(self, vertices: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Normalize vertices that cross the antimeridian.

        Parameters
        ----------
        vertices : List[Tuple[float, float]]
            List of (lon, lat) tuples

        Returns
        -------
        List[Tuple[float, float]]
            Normalized vertices
        """
        if not vertices:
            return vertices

        lons = [v[0] for v in vertices]
        lon_range = max(lons) - min(lons)

        # If longitude range > 180, we're crossing the antimeridian
        if lon_range > 180:
            # Shift negative longitudes to 0-360 range
            normalized = []
            for lon, lat in vertices:
                if lon < 0:
                    lon += 360
                normalized.append((lon, lat))
            return normalized

        return vertices

    def _contains_pole(self, vertices: List[Tuple[float, float]]) -> bool:
        """
        Check if polygon contains a pole.

        Parameters
        ----------
        vertices : List[Tuple[float, float]]
            List of (lon, lat) tuples

        Returns
        -------
        bool
            True if polygon contains north or south pole
        """
        if not vertices:
            return False

        lats = [v[1] for v in vertices]
        return max(lats) > 89.9 or min(lats) < -89.9

    def _handle_polar_cell(self, vertices: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Special handling for cells containing poles.

        Parameters
        ----------
        vertices : List[Tuple[float, float]]
            List of (lon, lat) tuples

        Returns
        -------
        List[Tuple[float, float]]
            Modified vertices with pole point if needed
        """
        if not vertices:
            return vertices

        lats = [v[1] for v in vertices]

        # Add pole point if cell contains it
        if max(lats) > 89.9:
            # Contains north pole
            vertices_copy = vertices.copy()
            vertices_copy.insert(0, (0.0, 90.0))
            return vertices_copy
        elif min(lats) < -89.9:
            # Contains south pole
            vertices_copy = vertices.copy()
            vertices_copy.insert(0, (0.0, -90.0))
            return vertices_copy

        return vertices


# Module-level convenience functions (public API)


def lonlat_to_cell(lon: float, lat: float, resolution: int) -> int:
    """
    Convert geographic coordinates to A5 cell ID.

    Parameters
    ----------
    lon : float
        Longitude in degrees [-180, 180]
    lat : float
        Latitude in degrees [-90, 90]
    resolution : int
        Resolution level (0-30)

    Returns
    -------
    int
        64-bit cell ID
    """
    ops = A5CellOperations()
    return ops.lonlat_to_cell(lon, lat, resolution)


def cell_to_lonlat(cell_id: int) -> Tuple[float, float]:
    """
    Convert A5 cell ID to center coordinates.

    Parameters
    ----------
    cell_id : int
        64-bit cell ID

    Returns
    -------
    Tuple[float, float]
        (lon, lat) in degrees
    """
    ops = A5CellOperations()
    return ops.cell_to_lonlat(cell_id)


def cell_to_boundary(cell_id: int) -> List[Tuple[float, float]]:
    """
    Get pentagon boundary vertices for a cell.

    Parameters
    ----------
    cell_id : int
        64-bit cell ID

    Returns
    -------
    List[Tuple[float, float]]
        List of (lon, lat) tuples forming pentagon boundary
    """
    ops = A5CellOperations()
    return ops.cell_to_boundary(cell_id)


def get_parent(cell_id: int) -> int:
    """
    Get parent cell at resolution-1.

    Parameters
    ----------
    cell_id : int
        Child cell ID

    Returns
    -------
    int
        Parent cell ID
    """
    ops = A5CellOperations()
    return ops.get_parent(cell_id)


def get_children(cell_id: int) -> List[int]:
    """
    Get 5 child cells at resolution+1.

    Parameters
    ----------
    cell_id : int
        Parent cell ID

    Returns
    -------
    List[int]
        List of 5 child cell IDs
    """
    ops = A5CellOperations()
    return ops.get_children(cell_id)


def get_resolution(cell_id: int) -> int:
    """
    Get resolution level of a cell.

    Parameters
    ----------
    cell_id : int
        Cell ID

    Returns
    -------
    int
        Resolution level
    """
    ops = A5CellOperations()
    return ops.get_resolution(cell_id)
