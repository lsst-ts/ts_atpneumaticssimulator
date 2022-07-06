.. py:currentmodule:: lsst.ts.atpneumaticssimulator

.. _lsst.ts.atpneumaticssimulator:

#############################
lsst.ts.atpneumaticssimulator
#############################

.. image:: https://img.shields.io/badge/Project Metadata-gray.svg
    :target: https://ts-xml.lsst.io/index.html#index-csc-table-atpneumatics
.. image:: https://img.shields.io/badge/SAL\ Interface-gray.svg
    :target: https://ts-xml.lsst.io/sal_interfaces/ATPneumatics.html
.. image:: https://img.shields.io/badge/GitHub-gray.svg
    :target: https://github.com/lsst-ts/ts_atpneumaticssimulator
.. image:: https://img.shields.io/badge/Jira-gray.svg
    :target: https://jira.lsstcorp.org/issues/?jql=project%3DDM%20AND%20labels%3Dts_atpneumaticssimulator

A simulator for the auxiliary telescope pneumatics control system (ATPneumatics CSC).

.. _lsst.ts.atpneumaticssimulator-using:

User Guide
==========

The package is compatible with LSST DM's ``scons`` build system and ``eups`` package management system.
Assuming you have the basic LSST DM stack installed you can do the following, from within the package directory:

* ``setup -r .`` to setup the package and dependencies.
* ``scons`` to build the package and run unit tests.
* ``scons install declare`` to install the package and declare it to eups.
* ``package-docs build`` to build the documentation.
  This requires ``documenteer``; see `building single package docs`_ for installation instructions.

.. _building single package docs: https://developer.lsst.io/stack/building-single-package-docs.html

With the package built and set up you can run the simulator using:

    run_atpneumatics_simulator

.. _lsst.ts.atpneumaticssimulator-contributing:

Contributing
============

``lsst.ts.atpneumaticssimulator`` is developed at https://github.com/lsst-ts/ts_atpneumaticssimulator.
You can find Jira issues for this module using `labels=ts_atpneumaticssimulator <https://jira.lsstcorp.org/issues/?jql=project%3DDM%20AND%20labels%3Dts_atpneumaticssimulator>`_.

.. _lsst.ts.atpneumaticssimulator-pyapi:

Python API reference
====================

.. automodapi:: lsst.ts.atpneumaticssimulator
   :no-main-docstr:

Version History
===============

.. toctree::
    version_history
    :maxdepth: 1
