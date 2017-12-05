.. Sankey-view documentation master file, created by
   sphinx-quickstart on Wed Nov 15 20:55:44 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to sankeyview's documentation!
=======================================

.. toctree::
   :maxdepth: 2
   :hidden:

   introduction
   introduction/Introductory example
   jupyter
   api


.. image:: sankeyview_overview.png

Sankeyview generates Sankey diagrams from a dataset of flows. For a descriptive
introduction, see the paper `Hybrid Sankey diagrams: Visual analysis of
multidimensional data for understanding resource use
<https://doi.org/10.1016/j.resconrec.2017.05.002>`_. For a more hands-on
introduction, read on.

Installation
============

Install sankeyview using pip:

.. code-block:: shell

    $ pip install sankeyview

If you use Jupyter notebooks -- a good way to get started -- you will also want
to install `ipysankeywidget <https://github.com/ricklupton/ipysankeywidget>`_,
an IPython widget to interactively display Sankey diagrams::

    $ pip install ipysankeywidget
    $ jupyter nbextension enable --py --sys-prefix ipysankeywidget

.. note::

    If this is the first time you have installed IPython widgets, you also need to
    make sure they are enabled::

        $ jupyter nbextension enable --py --sys-prefix widgetsnbextension

    If you use multiple virtualenvs or conda environments, make sure
    ``ipywidgets`` and ``ipysankeywidget`` are installed and enabled in both the
    environment running the notebook server and the kernel.

Getting started
===============

Start with the :ref:`introduction`, which introduces the concepts used to
generate and manipulate Sankey diagrams.

The easiest way to use sankeyview is through the interactive :ref:`Jupyter-interface`.

Alternatively, for more control you can use the :ref:`full-api`.

Citing sankeyview
=================

If sankeyview has been significant in a project that leads to a publication,
please acknowledge that by citing `the paper linked above
<https://doi.org/10.1016/j.resconrec.2017.05.002>`_:

    R. C. Lupton and J. M. Allwood, ‘Hybrid Sankey diagrams: Visual analysis of
       multidimensional data for understanding resource use’, Resources,
       Conservation and Recycling, vol. 124, pp. 141–151, Sep. 2017. DOI:
       10.1016/j.resconrec.2017.05.002


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
