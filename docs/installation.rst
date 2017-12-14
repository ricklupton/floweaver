.. _insta:

Installation
============

See below for more detailed instructions for Linux, Windows and OS X. In brief: 
install sankeyview using pip:

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

Install on Windows
------------------

Sankeyview requries the latest version of Python to be installed. This can be done by installing the Anaconda platform from `Link here <https://www.anaconda.com/download/>`_ .

The procedure described in section :ref:`insta` should be performed in the Anaconda Prompt, which can be found among the installed programs.

To open Jupyter Notebook and begin to work on the Sankey. Write in the Anaconda Prompt the following

.. code-block:: shell

    $ jupyter notebook

Install on macOS
----------------

Sankeyview requries the latest version of Python to be installed. This can be done by installing the Anaconda platform from `Link here <https://www.anaconda.com/download/>`_ .

The procedure described in section :ref:`insta` should be performed in the Command Line

To open Jupyter Notebook and begin to work on the Sankey. Write in the Command Line the following

.. code-block:: shell

    $ jupyter notebook

[not sure about this :D]