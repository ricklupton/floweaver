**floweaver** takes a database of flow data and transforms it into a Sankey
diagram. It implements the approach described in the paper `Hybrid Sankey diagrams: Visual analysis of multidimensional data for understanding resource use <https://doi.org/10.1016/j.resconrec.2017.05.002>`_.

Example: `Fruit - complete example.ipynb <http://nbviewer.jupyter.org/github/ricklupton/floweaver/blob/master/examples/Fruit%20-%20complete%20example.ipynb>`_

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.161970.svg

Installation
------------

Since floweaver depends on pandas and numpy, it's easiest to install those
using `Anaconda or Miniconda <https://www.continuum.io/downloads>`_.

Then install floweaver using pip:

.. code-block:: console

   pip install floweaver


Jupyter notebook
----------------

To use with the Jupyter notebook, the `ipysankeywidget
<https://github.com/ricklupton/ipysankeywidget>`_ package is also needed.

Contributions to Documentation
------------------------------

For Windows:
1. *Required software*
Anaconda, Github Desktop App
	1.1 Install pandoc package
	1.2 Clone Github Repository using the following URL: https://github.com/ricklupton/floweaver.git

2. *Modify Content*
The content is kept in the \docs directory. Each page is saved as a text file formatted in reStructured text

3. *Save Modifications*
To save the changes made to the content, open the Anaconda Prompt, go to the \floweaver\docs directory
and run 
.. code-block:: console

   make.bat html



