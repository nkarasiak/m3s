"""
Canonical grid-system class registry.

The single map of grid-system name -> grid *class*. This is the one place that
knows the set of grids and how to construct one at any precision (see CONTEXT.md
"Registry"). It lives in its own module, not in ``m3s/__init__.py`` (which
imports ``m3s.api``) so that lower layers -- ``GridConverter``,
``PrecisionSelector`` -- can resolve a grid by name without an import cycle.

The singleton/wrapper registry (``m3s/__init__.py::_GRID_REGISTRY``) and
``GridConverter`` both build on this map rather than re-listing the grids.
"""

from .a5 import A5Grid
from .base import BaseGrid
from .csquares import CSquaresGrid
from .eaquad import EAQuadGrid
from .gars import GARSGrid
from .geohash import GeohashGrid
from .h3 import H3Grid
from .maidenhead import MaidenheadGrid
from .mgrs import MGRSGrid
from .pluscode import PlusCodeGrid
from .quadkey import QuadkeyGrid
from .rhealpix import RHEALPixGrid
from .s2 import S2Grid
from .slippy import SlippyGrid

# Name -> grid class. The canonical set of grid systems.
GRID_CLASSES: dict[str, type[BaseGrid]] = {
    "a5": A5Grid,
    "geohash": GeohashGrid,
    "mgrs": MGRSGrid,
    "h3": H3Grid,
    "quadkey": QuadkeyGrid,
    "s2": S2Grid,
    "slippy": SlippyGrid,
    "csquares": CSquaresGrid,
    "gars": GARSGrid,
    "maidenhead": MaidenheadGrid,
    "pluscode": PlusCodeGrid,
    "eaquad": EAQuadGrid,
    "rhealpix": RHEALPixGrid,
}

_NAME_BY_CLASS: dict[type[BaseGrid], str] = {
    cls: name for name, cls in GRID_CLASSES.items()
}


def name_for_class(grid_class: type[BaseGrid]) -> str:
    """
    Canonical registry name for a grid class (reverse of :data:`GRID_CLASSES`).

    Lets a holder of a grid class (e.g. a ``GridWrapper``) recover the name a
    name-based consumer such as ``PrecisionSelector`` expects.
    """
    return _NAME_BY_CLASS[grid_class]
