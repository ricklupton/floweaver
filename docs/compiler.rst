Compiling SankeyDefinitions
===========================

The :func:`compile_sankey_definition` function converts a :ref:`sdd` to a
:class:`WeaverSpec`. This can then be passed to :func:`execute_weave` to apply
to a specific :ref:`dataset`, or saved to JSON format and applied to datasets
later using the Python or Javascript implementations.

.. autofunction:: floweaver.compile_sankey_definition

.. autofunction:: floweaver.execute_weave

Compiled specs
--------------

.. automodule:: floweaver.compiler.spec
   :members:
