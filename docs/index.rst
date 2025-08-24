M3S: Multi Spatial Subdivision System
=====================================

.. raw:: html

   <div style="text-align: center; margin: 20px 0;">
       <h2 style="color: #336790; margin-bottom: 10px;">Unified Spatial Grid Systems for Python</h2>
       <p style="font-size: 1.2em; color: #666; margin-bottom: 30px;">
           A comprehensive toolkit for working with multiple spatial indexing systems
       </p>
   </div>

M3S (Multi Spatial Subdivision System) is a powerful Python library that provides a unified interface for working with various spatial grid systems including **Geohash**, **MGRS** (Military Grid Reference System), **H3** (Uber's Hexagonal Hierarchical Spatial Index), and many more.

.. grid:: 3

   .. grid-item-card:: 🌍 Multi-Grid Support
      :class-header: bg-light

      Support for 10+ spatial grid systems including Geohash, MGRS, H3, S2, QuadKey, and more with a consistent API.

   .. grid-item-card:: ⚡ Performance Optimized
      :class-header: bg-light

      Built with performance in mind, supporting both CPU and GPU acceleration for large-scale spatial operations.

   .. grid-item-card:: 🔧 Easy Integration
      :class-header: bg-light

      Seamless integration with GeoPandas, Shapely, and the broader Python geospatial ecosystem.

Getting Started
===============

Installation
------------

Install M3S using pip:

.. code-block:: bash

   pip install m3s

Or with conda:

.. code-block:: bash

   conda install -c conda-forge m3s

Quick Example
-------------

Get started with M3S in just a few lines of code:

.. code-block:: python

   import geopandas as gpd
   from shapely.geometry import Point
   from m3s import H3Grid, GeohashGrid, MGRSGrid

   # Create sample locations
   gdf = gpd.GeoDataFrame({
       'city': ['New York', 'London', 'Tokyo'],
       'geometry': [
           Point(-74.0060, 40.7128),  # NYC
           Point(-0.1278, 51.5074),   # London
           Point(139.6503, 35.6762)   # Tokyo
       ]
   }, crs="EPSG:4326")

   # Generate different grid systems
   h3_grid = H3Grid(resolution=8)
   h3_cells = h3_grid.intersects(gdf)

   geohash_grid = GeohashGrid(precision=6)
   geohash_cells = geohash_grid.intersects(gdf)

   print(f"Generated {len(h3_cells)} H3 cells and {len(geohash_cells)} Geohash cells")

Supported Grid Systems
======================

.. list-table::
   :header-rows: 1
   :widths: 20 30 25 25

   * - Grid System
     - Description
     - Use Cases
     - Coverage
   * - **H3**
     - Hexagonal hierarchical spatial index
     - Location analytics, ride-sharing
     - Global
   * - **Geohash**
     - Base-32 string location encoding
     - Caching, databases
     - Global
   * - **MGRS**
     - Military Grid Reference System
     - Military, survey applications
     - Global (UTM-based)
   * - **S2**
     - Google's spherical geometry library
     - Large-scale geo applications
     - Global
   * - **QuadKey**
     - Microsoft's tile system
     - Web mapping, Bing Maps
     - Global

Key Features
============

🎯 **Unified API**
   Consistent interface across all supported grid systems - learn once, use everywhere.

🔄 **Format Conversion**
   Easy conversion between different grid systems and coordinate formats.

📊 **GeoPandas Integration**
   Native support for GeoPandas GeoDataFrames with spatial operations.

🚀 **High Performance**
   Optimized implementations with optional GPU acceleration support.

📈 **Scalable Operations**
   Handle everything from single points to massive datasets efficiently.

🛠️ **Extensible Design**
   Easy to add new grid systems and extend functionality.

Documentation
=============

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   auto_examples/index

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api
   changelog

Community & Support
===================

- 📚 **Documentation**: Complete API reference and examples
- 🐛 **Issue Tracker**: `GitHub Issues <https://github.com/nkarasiak/m3s/issues>`_
- 💬 **Discussions**: `GitHub Discussions <https://github.com/nkarasiak/m3s/discussions>`_
- 📧 **Contact**: Nicolas Karasiak

License
=======

M3S is released under the MIT License. See the `LICENSE <https://github.com/nkarasiak/m3s/blob/main/LICENSE>`_ file for details.

----

.. raw:: html

   <div style="text-align: center; margin: 40px 0 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px;">
       <p style="margin: 0; color: #666;">
           Made with ❤️ by the M3S team | 
           <a href="https://github.com/nkarasiak/m3s" style="text-decoration: none;">⭐ Star us on GitHub</a>
       </p>
   </div>