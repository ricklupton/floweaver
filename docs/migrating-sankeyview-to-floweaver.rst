Migrating from sankeyview
=========================

Starting with version 2.0, *sankeyview* has been renamed to *floWeaver*. At the
same time, there were a few changes to tidy up the API and make it more
flexible. This document describes the steps needed to update from an earlier
version to *floWeaver*.

Imports
-------

Where you had this before:

.. code-block:: python

    from sankeyview import *
    from sankeyview.jupyter import show_sankey

You should now have one of the following:

.. code-block:: python

   # More explicit about where names are coming from: use e.g. "fw.Dataset"
   import floweaver as fw

   # Less typing: use just e.g. "Dataset"
   from floweaver import *

``show_sankey`` function
------------------------

The ``show_sankey`` function (from module ``sankeyview.jupyter``) aimed to
provide an easy interface for showing Sankey diagrams in Jupyter notebooks, but
it was limited in its flexibility and had grown a long and confusing arguments
list. It has been replaced by the :func:`floweaver.weave` function.

For example, this old code:

.. code-block:: python

   show_sankey(sdd, dataset, width=800, height=500)

now becomes:

.. code-block:: python

   weave(sdd, dataset).to_widget(width=800, height=500)

For more details see :func:`floweaver.weave` and :class:`floweaver.SankeyData`.

Link colours
------------

While basic use should continue to work with the minor changes above, more
complicated uses involving these parameters of ``show_sankey`` will need to be
rewritten:

- ``agg_measures``
- ``hue``

See the `colour scales tutorial <tutorials/colour-scales.html>`_ for more details.
