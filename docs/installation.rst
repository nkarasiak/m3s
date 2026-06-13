Installation
============

Install
-------

M3S ships a Python package and a JavaScript/WASM build that share one Rust
core, so both produce identical cell geometry.

.. tab-set::

   .. tab-item:: Python

      The easiest way to install M3S is from PyPI using pip:

      .. code-block:: bash

         pip install m3s

   .. tab-item:: JavaScript

      No npm package is published yet — build the two WASM targets from source
      with `wasm-pack <https://rustwasm.github.io/wasm-pack/>`_, then import the
      ergonomic wrapper directly:

      .. code-block:: bash

         git clone https://github.com/nkarasiak/m3s.git
         cd m3s/bindings/js
         wasm-pack build --target nodejs --out-dir pkg      # Node build
         wasm-pack build --target web    --out-dir pkg-web  # browser build

      See the :doc:`javascript` guide for the full API.

Install from Source
-------------------

You can also install M3S directly from the source repository:

.. code-block:: bash

   git clone https://github.com/nkarasiak/m3s.git
   cd m3s
   pip install .

Development Installation
------------------------

For development, M3S uses `uv <https://docs.astral.sh/uv/>`_ to manage a
reproducible environment. Clone the repository and run ``uv sync``:

.. code-block:: bash

   git clone https://github.com/nkarasiak/m3s.git
   cd m3s
   uv sync

This creates a ``.venv`` (interpreter pinned by ``.python-version``) from
``uv.lock`` and installs the default ``dev`` dependency group, giving a
complete dev setup. Run tooling with ``uv run`` (e.g. ``uv run pytest``).
The ``dev`` group includes:

* pytest / pytest-cov for testing
* black, isort, ruff, flake8 for formatting and linting
* mypy for type checking
* sphinx + sphinx-gallery (and matplotlib, contextily, folium) for the docs

Verify Installation
-------------------

To verify that M3S is installed correctly, run:

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s
         print(m3s.__version__)

         # Get an H3 cell at New York City  (lon, lat)
         cell = m3s.H3.from_geometry((-74.0060, 40.7128))
         print(f"H3 cell: {cell.id}")

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "./bindings/js/wrapper/index.node.js";
         await m3s.ready();

         // Get an H3 cell at New York City  (lon, lat, precision)
         const cell = m3s.H3.fromPoint(-74.0060, 40.7128, 7);
         console.log("H3 cell:", cell.id);

Optional Dependencies
---------------------

For visualization examples:

.. code-block:: bash

   pip install matplotlib

For testing:

.. code-block:: bash

   pip install pytest pytest-cov