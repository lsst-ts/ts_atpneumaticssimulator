.. py:currentmodule:: lsst.ts.ATPneumaticsSimulator

.. _lsst.ts.ATPneumaticsSimulator:

#############################
lsst.ts.ATPneumaticsSimulator
#############################

A simulator for the auxiliary telescope pneumatics control system (ATPneumatics CSC).

.. _lsst.ts.ATPneumaticsSimulator-using:

Using lsst.ts.ATPneumaticsSimulator
===================================

The package is compatible with LSST DM's ``scons`` build system and ``eups`` package management system.
Assuming you have the basic LSST DM stack installed you can do the following, from within the package directory:

* ``setup -r .`` to setup the package and dependencies.
* ``scons`` to build the package and run unit tests.
* ``scons install declare`` to install the package and declare it to eups.
* ``package-docs build`` to build the documentation.
  This requires ``documenteer``; see `building single package docs`_ for installation instructions.

.. _building single package docs: https://developer.lsst.io/stack/building-single-package-docs.html

With the package built and set up you can run the simulator using:

    run_atpneumatics_simulator.py

.. _lsst.ts.ATPneumaticsSimulator-contributing:

Contributing
============

``lsst.ts.ATPneumaticsSimulator`` is developed at https://github.com/lsst-ts/ts_ATPneumaticsSimulator.
You can find Jira issues for this module using `labels=ts_ATPneumaticsSimulator <https://jira.lsstcorp.org/issues/?jql=project%20%3D%20DM%20AND%20labels%20%20%3D%20ts_ATPneumaticsSimulator>`_.

.. _lsst.ts.ATPneumaticsSimulator-pyapi:

Python API reference
====================

.. automodapi:: lsst.ts.ATPneumaticsSimulator
   :no-main-docstr:

Version History
===============

.. toctree::
    version_history
    :maxdepth: 1
