Changelog
=========

Unreleased
----------

* Added an experimental "compiler" which converts a SankeyDefinition into a
  complete recipe for the Sankey diagram, which can be quickly and simply
  applied to a dataset later. This enables (somewhat) faster calculation of
  Sankey diagrams against many datasets, but more importantly makes it feasible
  to do the calculations in other languages/contexts, since all the complexity
  and interpretation of the SankeyDefinition has been done up-front. An
  experimental JavaScript library is included which can interpret the compiled
  specs.
* Compiled specs now route flows in two stages: a selection tree routes each
  flow to its Bundle(s), then a tree for each Bundle routes it to edges. This
  avoids a combinatorial explosion when compiling large diagrams with many
  Elsewhere flows and partitions. Both trees branch on classes of values that
  the routing rules treat identically, rather than on individual values, which
  keeps them small and quick to compile. The spec format version is now 2.1,
  with ``value_classes``, ``selection_tree`` and ``bundle_trees`` in place of
  ``routing_tree``; specs with a single combined ``routing_tree`` can still be
  loaded and executed, in Python and JavaScript.

v2.0.0 (renamed to floWeaver)
-----------------------------

* sankeyview is now called floWeaver!
* There is a new top-level interface to creating a Sankey diagram, the
  :func:`floweaver.weave` function. This gives more flexibility about the
  appearance of the diagram, and lets you save the results in different formats
  (other than showing directly in the Jupyter notebook), while still being simple
  to use for the most common cases.
* No longer any need for ``from sankeyview.jupyter import show_sankey``; use
  :func:`floweaver.weave` instead.
* New way to specify link colours using :class:`floweaver.CategoricalScale` and
  :class:`floweaver.QuantitativeScale`, replacing ``hue`` and related arguments to
  ``show_sankey``. See :ref:`/tutorials/colour-scales.ipynb` for examples.

