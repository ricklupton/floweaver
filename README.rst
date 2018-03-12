floWeaver
=========

Many kinds of data can be thought of as 'flows': energy and materials moving
through industry, money flowing through the economy, telephone lines moving
between providers, voters moving between parties. **floWeaver** is an
open-source framework for exchanging and analysing flow data, and visualising it
using Sankey diagrams.

For example, here is some data on flows of fruit from farms to customers:

.. image:: docs/demo_table.png

floWeaver can visualise this as a variety of Sankey diagrams depending on what
you want to show:

.. image:: docs/demo_animation/demo.gif

.. image:: https://badge.fury.io/py/floweaver.svg
    :target: https://badge.fury.io/py/floweaver
.. image:: https://readthedocs.org/projects/floweaver/badge/?version=latest
    :target: http://floweaver.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status
.. image:: https://travis-ci.org/ricklupton/floweaver.svg?branch=master
    :target: https://travis-ci.org/ricklupton/floweaver
.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.161970.svg
    :target: https://doi.org/10.5281/zenodo.596249

What are we doing?
------------------

Although there are a variety of tools for working with flow data and Sankey
diagrams in particular contexts, there are no open data formats for sharing data
across domains, and limited open tools for processing and visualisation.


It builds on the approach described in the paper `Hybrid Sankey diagrams: Visual
analysis of multidimensional data for understanding resource use
<https://doi.org/10.1016/j.resconrec.2017.05.002>`_.

Get started
-----------

🚀 **Try floWeaver with no installation:** `Quickstart tutorial
<https://mybinder.org/v2/gh/ricklupton/floweaver/master?filepath=docs%2Ftutorials%2Fquickstart.ipynb>`_.

floWeaver is a Python package, but you can use it as a data analysis tool even
without too much familiarity with Python. The best way to get started is to use
it in Jupyter notebooks; see the `installation page
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

Contributing 🎁
_______________

Contributions are welcome! See the `contributing page in the docs
<https://floweaver.readthedocs.io/en/latest/contributing.html>`_.
