floWeaver
=========

**floWeaver** takes a database of flow data and transforms it into a Sankey
diagram. It implements the approach described in the paper `Hybrid Sankey
diagrams: Visual analysis of multidimensional data for understanding resource
use <https://doi.org/10.1016/j.resconrec.2017.05.002>`_.

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.161970.svg

Try it!
-------

Try floWeaver with no installation: `Quickstart tutorial <https://mybinder.org/v2/gh/ricklupton/floweaver/master?filepath=docs%2Ftutorials%2Fquickstart.ipynb>`_.

Installation
------------

floWeaver is a Python package, but you can use it as a data analysis tool even
without too much familiarity with Python. The best way to get started is to use
it in Jupyter notebooks; you can try it out right now in your browser without
installing anything `using MyBinder
<https://mybinder.org/v2/gh/ricklupton/floweaver/master?filepath=docs%2Ftutorials%2Fquickstart.ipynb>`_.

To install locally see the `installation page
<https://floweaver.readthedocs.io/en/latest/installation.html>`_ for full
details. In brief, floWeaver depends on pandas and numpy and it's easiest to
install those using `Anaconda or Miniconda
<https://www.continuum.io/downloads>`_. Then install floweaver using pip:

.. code-block:: console

   pip install floweaver

You likely also want the `ipysankeywidget
<https://github.com/ricklupton/ipysankeywidget>`_ package to show Sankey
diagrams in the Jupyter notebook. Install this using pip and enable:

.. code-block:: console

   pip install ipysankeywidget
   jupyter nbextension enable --py --sys-prefix ipysankeywidget

Contributing
------------

Contributions are welcome! See the `contributing page in the docs
<https://floweaver.readthedocs.io/en/latest/contributing.html>`_.
