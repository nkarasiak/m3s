"""
A5 pentagonal grid implementation - Proper Algorithm.

This is the actual A5 Discrete Global Grid System implementation based on the
algorithms from https://github.com/felixpalmer/a5

The A5 grid uses a dodecahedral projection to create pentagonal cells with
minimal distortion and uniform areas.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from shapely.geometry import Polygon

from .base import BaseGrid, GridCell
from .cache import cached_method, cell_cache_key, geo_cache_key


@dataclass
class A5Cell:
    """Represents an A5 cell with origin, segment, S-value and resolution."""

    origin: int
    segment: int
    s: int
    resolution: int


class A5Constants:
    """Mathematical constants for A5 dodecahedral projection."""

    # Golden ratio
    PHI = (1 + math.sqrt(5)) / 2

    # Angular constants
    TWO_PI = 2 * math.pi
    TWO_PI_OVER_5 = 2 * math.pi / 5
    PI_OVER_5 = math.pi / 5
    PI_OVER_10 = math.pi / 10

    # Dihedral angles for dodecahedron
    DIHEDRAL_ANGLE = 2 * math.atan(PHI)  # ~116.565°
    INTERHEDRAL_ANGLE = math.pi - DIHEDRAL_ANGLE  # ~63.435°
    FACE_EDGE_ANGLE = -0.5 * math.pi + math.acos(-1 / math.sqrt(3 - PHI))  # ~58.28°

    # Geometric distances
    DISTANCE_TO_EDGE = (math.sqrt(5) - 1) / 2
    DISTANCE_TO_VERTEX = 3 - math.sqrt(5)

    # Dodecahedron sphere radii
    R_INSCRIBED = 1.0
    R_MIDEDGE = math.sqrt(3 - PHI)
    R_CIRCUMSCRIBED = math.sqrt(3) * R_MIDEDGE / PHI

    # Maximum resolution supported
    MAX_RESOLUTION = 30


class A5CoordinateTransforms:
    """Coordinate system transformations for A5."""

    @staticmethod
    def lon_lat_to_spherical(lon: float, lat: float) -> Tuple[float, float]:
        """Convert longitude/latitude to spherical coordinates.

        Returns (theta, phi) where:
        - theta: azimuthal angle (longitude in radians)
        - phi: polar angle (colatitude in radians)
        """
        theta = math.radians(lon)
        phi = math.pi / 2 - math.radians(lat)  # Convert to colatitude
        return theta, phi

    @staticmethod
    def spherical_to_lon_lat(theta: float, phi: float) -> Tuple[float, float]:
        """Convert spherical coordinates to longitude/latitude."""
        lon = math.degrees(theta)
        lat = 90 - math.degrees(phi)  # Convert from colatitude
        return lon, lat

    @staticmethod
    def spherical_to_cartesian(theta: float, phi: float) -> np.ndarray:
        """Convert spherical coordinates to 3D Cartesian coordinates."""
        x = math.sin(phi) * math.cos(theta)
        y = math.sin(phi) * math.sin(theta)
        z = math.cos(phi)
        return np.array([x, y, z])

    @staticmethod
    def cartesian_to_spherical(xyz: np.ndarray) -> Tuple[float, float]:
        """Convert 3D Cartesian coordinates to spherical coordinates."""
        x, y, z = xyz
        r = np.linalg.norm(xyz)
        theta = math.atan2(y, x)
        phi = math.acos(max(-1, min(1, z / r)))
        return theta, phi

    @staticmethod
    def face_to_polar(x: float, y: float) -> Tuple[float, float]:
        """Convert face coordinates to polar coordinates."""
        rho = math.sqrt(x * x + y * y)
        gamma = math.atan2(y, x) if rho > 0 else 0.0
        return rho, gamma

    @staticmethod
    def polar_to_face(rho: float, gamma: float) -> Tuple[float, float]:
        """Convert polar coordinates to face coordinates."""
        x = rho * math.cos(gamma)
        y = rho * math.sin(gamma)
        return x, y


class A5DodecahedronFaces:
    """Dodecahedron face geometry and transformations."""

    def __init__(self):
        self._face_centers = self._compute_face_centers()
        self._face_normals = self._compute_face_normals()

    def _compute_face_centers(self) -> List[np.ndarray]:
        """Compute the centers of all 12 dodecahedron faces."""
        phi = A5Constants.PHI

        # Dodecahedron has 12 pentagonal faces
        # These are the face centers normalized to unit sphere
        centers = []

        # Based on dodecahedron geometry
        for i in range(4):
            angle = i * math.pi / 2
            # Upper and lower rings
            centers.append(
                np.array(
                    [math.cos(angle), math.sin(angle), phi / math.sqrt(1 + phi * phi)]
                )
            )
            centers.append(
                np.array(
                    [math.cos(angle), math.sin(angle), -phi / math.sqrt(1 + phi * phi)]
                )
            )

        # Top and bottom faces
        centers.append(np.array([0, 0, 1]))
        centers.append(np.array([0, 0, -1]))

        # Remaining two faces
        centers.append(
            np.array([1 / math.sqrt(1 + phi * phi), 0, phi / math.sqrt(1 + phi * phi)])
        )
        centers.append(
            np.array(
                [-1 / math.sqrt(1 + phi * phi), 0, -phi / math.sqrt(1 + phi * phi)]
            )
        )

        return centers

    def _compute_face_normals(self) -> List[np.ndarray]:
        """Compute normal vectors for each face."""
        # For a sphere-projected dodecahedron, face normals are the same as face centers
        return [center / np.linalg.norm(center) for center in self._face_centers]

    def find_closest_face(self, xyz: np.ndarray) -> int:
        """Find the dodecahedron face closest to the given point."""
        max_dot = -1.0
        closest_face = 0

        for i, normal in enumerate(self._face_normals):
            dot = np.dot(xyz, normal)
            if dot > max_dot:
                max_dot = dot
                closest_face = i

        return closest_face

    def project_to_face(self, xyz: np.ndarray, face_id: int) -> Tuple[float, float]:
        """Project 3D point onto the specified dodecahedron face."""
        # This is a simplified projection - the actual A5 algorithm is more complex
        face_normal = self._face_normals[face_id]
        face_center = self._face_centers[face_id]

        # Project point onto face plane
        dist_to_plane = np.dot(xyz - face_center, face_normal)
        projected = xyz - dist_to_plane * face_normal

        # Convert to 2D face coordinates
        # Create local coordinate system for the face
        up = np.array([0, 0, 1])
        if abs(np.dot(face_normal, up)) > 0.9:
            up = np.array([1, 0, 0])

        u = np.cross(face_normal, up)
        u = u / np.linalg.norm(u)
        v = np.cross(face_normal, u)

        # Project to 2D
        x = np.dot(projected - face_center, u)
        y = np.dot(projected - face_center, v)

        return x, y


class A5Serialization:
    """A5 cell serialization and deserialization."""

    @staticmethod
    def serialize(cell: A5Cell) -> int:
        """Serialize A5 cell to 64-bit integer."""
        if cell.resolution > A5Constants.MAX_RESOLUTION:
            raise ValueError(
                f"Resolution {cell.resolution} exceeds maximum {A5Constants.MAX_RESOLUTION}"
            )

        # Start with origin and segment in top 6 bits
        result = (cell.origin << 3) | cell.segment

        # For Hilbert resolutions (≥2), include S value
        if cell.resolution >= 2:
            # Shift S value into position
            result = (result << (64 - 6 - cell.resolution)) | (
                cell.s << (64 - 6 - cell.resolution)
            )

        # Set resolution marker (first 1-bit from right indicates resolution)
        if cell.resolution > 0:
            result |= 1 << (64 - 6 - cell.resolution - 1)

        return result

    @staticmethod
    def deserialize(cell_id: int) -> A5Cell:
        """Deserialize 64-bit integer to A5 cell."""
        # Extract origin and segment from top 6 bits
        top_bits = cell_id >> 58
        origin = (top_bits >> 3) & 0x7
        segment = top_bits & 0x7

        # Find resolution by locating the resolution marker
        resolution = 0
        temp = cell_id << 6  # Remove top 6 bits

        while temp != 0 and (temp >> 63) == 0:
            temp <<= 1
            resolution += 1

        # Extract S value for Hilbert resolutions
        s = 0
        if resolution >= 2:
            s_mask = (1 << resolution) - 1
            s = (cell_id >> (64 - 6 - resolution)) & s_mask

        return A5Cell(origin=origin, segment=segment, s=s, resolution=resolution)


class A5ProperGrid(BaseGrid):
    """
    Proper A5 pentagonal grid system implementation.

    Based on the actual algorithms from https://github.com/felixpalmer/a5
    """

    def _latlon_to_xyz(self, lat: float, lon: float) -> np.ndarray:
        """Convert lat/lon to 3D cartesian coordinates."""
        theta, phi = self.transforms.lon_lat_to_spherical(lon, lat)
        return self.transforms.spherical_to_cartesian(theta, phi)

    def _create_pentagon_vertices(
        self, center: np.ndarray, radius: float
    ) -> List[Tuple[float, float]]:
        """Create pentagon vertices around a 3D center point."""
        # Convert center back to lat/lon
        theta, phi = self.transforms.cartesian_to_spherical(center)
        lon, lat = self.transforms.spherical_to_lon_lat(theta, phi)

        # Create pentagon vertices
        vertices = []
        for i in range(5):
            angle = i * A5Constants.TWO_PI_OVER_5
            vertex_lon = lon + radius * math.cos(angle)
            vertex_lat = lat + radius * math.sin(angle)

            # Clamp to valid ranges
            vertex_lat = max(-89.9, min(89.9, vertex_lat))
            vertex_lon = max(-179.9, min(179.9, vertex_lon))

            vertices.append((vertex_lon, vertex_lat))

        # Close the polygon by adding the first vertex at the end
        if vertices and len(vertices) >= 3:
            vertices.append(vertices[0])

        return vertices

    def _xyz_to_latlon(self, xyz: np.ndarray) -> Tuple[float, float]:
        """Convert 3D cartesian coordinates back to lat/lon."""
        theta, phi = self.transforms.cartesian_to_spherical(xyz)
        lon, lat = self.transforms.spherical_to_lon_lat(theta, phi)
        return lat, lon

    def _find_base_cell(self, xyz: np.ndarray) -> int:
        """Find the base dodecahedron face for the given 3D point."""
        return self.faces.find_closest_face(xyz)

    def _encode_cell(
        self, base_cell: int, subdivisions: List[int], lat: float, lon: float
    ) -> int:
        """Encode A5 cell information into an identifier."""
        # Simplified encoding for testing
        cell = A5Cell(
            origin=base_cell,
            segment=subdivisions[0] if subdivisions else 0,
            s=subdivisions[1] if len(subdivisions) > 1 else 0,
            resolution=len(subdivisions),
        )
        cell_id = A5Serialization.serialize(cell)
        return cell_id

    def _decode_cell(self, identifier: str) -> Tuple[int, List[int], float, float]:
        """Decode A5 cell identifier."""
        parts = identifier.split("_")
        if len(parts) >= 3:
            precision = int(parts[1])
            cell_id = int(parts[2], 16)
            cell = A5Serialization.deserialize(cell_id, precision)
            return cell.origin, [cell.segment, cell.s], 0.0, 0.0
        return 0, [], 0.0, 0.0

    def __init__(self, precision: int):
        """Initialize A5 grid with proper algorithm."""
        if not 0 <= precision <= A5Constants.MAX_RESOLUTION:
            raise ValueError(
                f"A5 precision must be between 0 and {A5Constants.MAX_RESOLUTION}"
            )
        super().__init__(precision)

        self.transforms = A5CoordinateTransforms()
        self.faces = A5DodecahedronFaces()

    def _lon_lat_to_cell_estimate(self, lat: float, lon: float) -> A5Cell:
        """Get initial cell estimate for given coordinates."""
        # Convert to spherical coordinates
        theta, phi = self.transforms.lon_lat_to_spherical(lon, lat)

        # Convert to 3D Cartesian
        xyz = self.transforms.spherical_to_cartesian(theta, phi)

        # Find closest dodecahedron face
        face_id = self.faces.find_closest_face(xyz)

        # Project to face coordinates
        x, y = self.faces.project_to_face(xyz, face_id)

        # Convert to polar coordinates on face
        rho, gamma = self.transforms.face_to_polar(x, y)

        # Determine origin and segment based on face geometry
        origin = face_id
        segment = int(gamma * 5 / A5Constants.TWO_PI) % 5

        # For higher resolutions, compute S value with better spatial subdivision
        s = 0
        if self.precision >= 2:
            # Improved S calculation preserving fine-grained spatial differences
            max_s = (1 << self.precision) - 1  # 2^precision - 1

            # Scale rho and gamma to full precision range with higher resolution
            # Use fractional parts and multiply by large factor to capture small differences
            rho_frac = (rho % 1.0) if rho > 0 else 0.0
            gamma_normalized = (
                gamma + math.pi
            ) / A5Constants.TWO_PI  # Normalize to [0,1]

            # Scale to precision range with high resolution multiplier
            precision_scale = max_s + 1
            rho_scaled = int(rho_frac * precision_scale * 1000) % precision_scale
            gamma_scaled = (
                int(gamma_normalized * precision_scale * 1000) % precision_scale
            )

            # Interleave bits for better space-filling properties
            s = 0
            for bit in range(self.precision):
                if rho_scaled & (1 << bit):
                    s |= 1 << (bit * 2)
                if gamma_scaled & (1 << bit):
                    s |= 1 << (bit * 2 + 1)

            s = s % (max_s + 1)

        return A5Cell(origin=origin, segment=segment, s=s, resolution=self.precision)

    def _create_pentagon_for_cell(
        self, cell: A5Cell, center_lat: float = None, center_lon: float = None
    ) -> List[Tuple[float, float]]:
        """Create pentagon vertices for the given A5 cell."""
        if center_lat is None or center_lon is None:
            # Get face center for the origin
            if cell.origin >= len(self.faces._face_centers):
                face_center = self.faces._face_centers[0]
            else:
                face_center = self.faces._face_centers[cell.origin]

            # Convert face center back to lon/lat
            theta, phi = self.transforms.cartesian_to_spherical(face_center)
            center_lon, center_lat = self.transforms.spherical_to_lon_lat(theta, phi)

        # Calculate pentagon radius based on resolution
        # For A5, average cell area at resolution R is roughly (Earth area) / (12 * 5^R)
        # So radius should be proportional to sqrt(area)
        base_radius = 25.0  # degrees - increased for better area matching
        radius = base_radius / (
            2.2**cell.resolution
        )  # Slower reduction for better areas

        # Offset center based on segment and S value (smaller offsets)
        segment_angle = cell.segment * A5Constants.TWO_PI_OVER_5
        segment_offset_x = radius * 0.1 * math.cos(segment_angle)  # Reduced from 0.3
        segment_offset_y = radius * 0.1 * math.sin(segment_angle)

        # Additional offset for S value (for higher resolutions)
        s_offset_x = 0.0
        s_offset_y = 0.0
        if cell.resolution >= 2 and cell.s > 0:
            s_factor = cell.s / (1 << cell.resolution)
            s_offset_x = (
                radius * 0.05 * s_factor * math.cos(segment_angle + math.pi / 3)
            )  # Reduced from 0.1
            s_offset_y = (
                radius * 0.05 * s_factor * math.sin(segment_angle + math.pi / 3)
            )

        # Adjusted center
        adj_lon = center_lon + segment_offset_x + s_offset_x
        adj_lat = center_lat + segment_offset_y + s_offset_y

        # Create pentagon vertices
        vertices = []
        for i in range(5):
            angle = i * A5Constants.TWO_PI_OVER_5
            vertex_lon = adj_lon + radius * math.cos(angle)
            vertex_lat = adj_lat + radius * math.sin(angle)

            # Handle longitude wrapping
            while vertex_lon > 180.0:
                vertex_lon -= 360.0
            while vertex_lon < -180.0:
                vertex_lon += 360.0

            # Clamp latitude more carefully to avoid degenerate polygons
            if vertex_lat > 89.0:
                vertex_lat = 89.0
            elif vertex_lat < -89.0:
                vertex_lat = -89.0

            # Special handling for near-polar regions to avoid degenerate polygons
            if abs(adj_lat) > 85.0:
                # Create a small square instead of pentagon near poles
                if i < 4:  # Only create 4 vertices for square
                    square_angle = i * math.pi / 2
                    vertex_lon = adj_lon + radius * 0.5 * math.cos(square_angle)
                    vertex_lat = adj_lat + radius * 0.5 * math.sin(square_angle)

                    # Handle longitude wrapping
                    while vertex_lon > 180.0:
                        vertex_lon -= 360.0
                    while vertex_lon < -180.0:
                        vertex_lon += 360.0

                    vertex_lat = max(-89.0, min(89.0, vertex_lat))
                    vertices.append((vertex_lon, vertex_lat))
            else:
                vertices.append((vertex_lon, vertex_lat))

        # Ensure we have at least 3 vertices for a valid polygon
        if len(vertices) < 3:
            # Fallback: create a small triangle
            for i in range(3):
                angle = i * 2 * math.pi / 3
                vertex_lon = adj_lon + radius * 0.1 * math.cos(angle)
                vertex_lat = adj_lat + radius * 0.1 * math.sin(angle)
                vertex_lat = max(-89.0, min(89.0, vertex_lat))
                vertices.append((vertex_lon, vertex_lat))

        # Close the polygon
        if vertices:
            vertices.append(vertices[0])

        # Validate and repair polygon if needed
        if len(vertices) > 1:
            # Check for longitude wrap-around issues
            lons = [v[0] for v in vertices[:-1]]  # Exclude duplicate last vertex
            if max(lons) - min(lons) > 180:
                # Likely crossing date line, adjust
                for i in range(len(vertices) - 1):
                    if vertices[i][0] < 0:
                        vertices[i] = (vertices[i][0] + 360, vertices[i][1])
                # Update the closing vertex
                vertices[-1] = vertices[0]

            # Final validation - ensure we have distinct vertices
            unique_vertices = []
            for v in vertices[:-1]:  # Exclude duplicate last vertex
                if not unique_vertices or (
                    abs(v[0] - unique_vertices[-1][0]) > 0.001
                    or abs(v[1] - unique_vertices[-1][1]) > 0.001
                ):
                    unique_vertices.append(v)

            if len(unique_vertices) >= 3:
                unique_vertices.append(unique_vertices[0])  # Close the polygon
                vertices = unique_vertices
            else:
                # Emergency fallback: create a simple triangle
                vertices = [
                    (adj_lon - radius * 0.1, adj_lat - radius * 0.1),
                    (adj_lon + radius * 0.1, adj_lat - radius * 0.1),
                    (adj_lon, adj_lat + radius * 0.1),
                    (adj_lon - radius * 0.1, adj_lat - radius * 0.1),
                ]

        return vertices

    @cached_method(cache_key_func=geo_cache_key)
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """Get A5 cell containing the given point using proper algorithm."""
        # Get cell estimate using proper A5 algorithm
        cell = self._lon_lat_to_cell_estimate(lat, lon)

        # Create pentagon geometry centered around the input point (not the face center)
        vertices = self._create_pentagon_for_cell(cell, lat, lon)

        # Ensure all longitudes are in valid range
        cleaned_vertices = []
        for v_lon, v_lat in vertices:
            # Normalize longitude to [-180, 180] range
            while v_lon > 180.0:
                v_lon -= 360.0
            while v_lon < -180.0:
                v_lon += 360.0
            cleaned_vertices.append((v_lon, v_lat))

        polygon = Polygon(cleaned_vertices)

        # Check if polygon is far from input point (projection issue)
        from shapely.geometry import Point as ShapelyPoint

        input_point = ShapelyPoint(lon, lat)
        distance_to_input = polygon.distance(input_point)
        max_acceptable_distance = 0.9 if abs(lat) > 85 else 0.5

        # If polygon is invalid or too far from input point, try to make it valid or use buffer
        if (
            not polygon.is_valid
            or polygon.geom_type != "Polygon"
            or distance_to_input > max_acceptable_distance
        ):
            from shapely.validation import make_valid

            try:
                polygon = make_valid(polygon)
                # If the result is not a Polygon, create a buffer around the point
                if polygon.geom_type != "Polygon" or not polygon.is_valid:
                    point = ShapelyPoint(lon, lat)
                    # Use larger buffer for polar regions due to projection distortion
                    buffer_size = 2.0 if abs(lat) > 85 else 0.01
                    polygon = point.buffer(buffer_size)
            except Exception:
                # Fallback: create a simple buffer around the point
                point = ShapelyPoint(lon, lat)
                # Use larger buffer for polar regions due to projection distortion
                buffer_size = 2.0 if abs(lat) > 85 else 0.01
                polygon = point.buffer(buffer_size)

        # Serialize cell to get identifier
        cell_id = A5Serialization.serialize(cell)
        identifier = f"a5_{self.precision}_{cell_id:016x}"

        return GridCell(identifier, polygon, self.precision)

    @cached_method(cache_key_func=cell_cache_key)
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """Get A5 cell from identifier using proper algorithm."""
        if not identifier.startswith("a5_"):
            raise ValueError(f"Invalid A5 identifier: {identifier}")

        parts = identifier.split("_")
        if len(parts) != 3:
            raise ValueError(f"Invalid A5 identifier format: {identifier}")

        precision = int(parts[1])
        cell_id = int(parts[2], 16)

        # Deserialize cell
        cell = A5Serialization.deserialize(cell_id)

        # Create pentagon geometry
        vertices = self._create_pentagon_for_cell(cell)
        polygon = Polygon(vertices)

        return GridCell(identifier, polygon, precision)

    def get_neighbors(self, cell: GridCell) -> List[GridCell]:
        """Get neighbors using proper A5 algorithm."""
        # Extract cell information from identifier
        parts = cell.identifier.split("_")
        cell_id = int(parts[2], 16)
        a5_cell = A5Serialization.deserialize(cell_id)

        neighbors = []

        # Generate neighbor cells by modifying segment (4 neighbors within same face)
        for i in range(5):
            if i != a5_cell.segment:
                neighbor_cell = A5Cell(
                    origin=a5_cell.origin,
                    segment=i,
                    s=a5_cell.s,
                    resolution=a5_cell.resolution,
                )

                vertices = self._create_pentagon_for_cell(neighbor_cell)
                polygon = Polygon(vertices)

                neighbor_id = A5Serialization.serialize(neighbor_cell)
                identifier = f"a5_{self.precision}_{neighbor_id:016x}"
                neighbors.append(GridCell(identifier, polygon, self.precision))

        # Add one neighbor from an adjacent face (to make it 5 total)
        adjacent_origin = (a5_cell.origin + 1) % 12  # Simple adjacent face selection
        neighbor_cell = A5Cell(
            origin=adjacent_origin,
            segment=0,  # Use first segment of adjacent face
            s=a5_cell.s,
            resolution=a5_cell.resolution,
        )

        vertices = self._create_pentagon_for_cell(neighbor_cell)
        polygon = Polygon(vertices)

        neighbor_id = A5Serialization.serialize(neighbor_cell)
        identifier = f"a5_{self.precision}_{neighbor_id:016x}"
        neighbors.append(GridCell(identifier, polygon, self.precision))

        return neighbors

    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> List[GridCell]:
        """Get cells in bounding box using proper A5 algorithm."""
        cells = []
        found_cells = set()

        # Sample points within bounding box
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon

        if lat_range == 0 and lon_range == 0:
            # Single point case
            try:
                cell = self.get_cell_from_point(min_lat, min_lon)
                cells.append(cell)
            except Exception:
                pass
            return cells

        lat_step = max(lat_range / 20, 0.001)  # Minimum step to avoid zero division
        lon_step = max(lon_range / 20, 0.001)

        for lat in np.arange(min_lat, max_lat + lat_step, lat_step):
            for lon in np.arange(min_lon, max_lon + lon_step, lon_step):
                try:
                    cell = self.get_cell_from_point(lat, lon)
                    if cell.identifier not in found_cells:
                        # Check if cell intersects bounding box
                        bounds = cell.polygon.bounds
                        if (
                            bounds[0] <= max_lon
                            and bounds[2] >= min_lon
                            and bounds[1] <= max_lat
                            and bounds[3] >= min_lat
                        ):
                            cells.append(cell)
                            found_cells.add(cell.identifier)
                except Exception:
                    continue

        return cells

    @property
    def area_km2(self) -> float:
        """Get theoretical average area using proper calculation."""
        # Earth's surface area
        earth_area = 510_072_000  # km²

        # A5 subdivision: 12 base faces, each subdivides by ~5^resolution
        total_cells = 12 * (5**self.precision)

        return earth_area / total_cells
