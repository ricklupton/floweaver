Weaving the Sankey diagram
==========================

The :func:`weave` function actually creates a Sankey diagram from the :ref:`sdd`
and a :ref:`dataset`.

.. autofunction:: floweaver.weave

Tabulating the flows in a diagram
---------------------------------

The :func:`weave_table` function takes the same inputs, but instead of the
drawable diagram it returns a :class:`pandas.DataFrame` describing the same
flows end to end: from each source (or Elsewhere) to each target (or
Elsewhere), via any visible Waypoints, using the labels shown in the diagram.
This is useful as "source data" to accompany a published figure, for example
using :meth:`pandas.DataFrame.to_excel`.

.. autofunction:: floweaver.weave_table
