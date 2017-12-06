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
