.. py:currentmodule:: lsst.ts.ATPneumaticsSimulator

.. _lsst.ts.ATPneumaticsSimulator.version_history:

###############
Version History
###############

v0.5.3
======

* Add black to conda test dependencies

v0.5.2
======

* Add ``tests/test_black.py`` to verify that files are formatted with black.
  This requires ts_salobj 5.11 or later.
* Update ``tests/test_csc.py`` to use ``BaseCscTestCase.check_bin_script``.
* Update ``.travis.yml`` to remove ``sudo: false`` to github travis checks pass once again.

Requirements:

* ts_salobj 5.11
* ts_xml 4
* ts_idl 1


v0.5.1
======

* Include conda package build configuration.
* Added a Jenkinsfile to support continuous integration and to build conda packages.

Requirements:

* ts_salobj 5.4
* ts_xml 4
* ts_idl 1

v0.5.0
======

Major changes:

* Modernize CSC unit test to use `lsst.ts.salobj.BaseCscTestCase`.
* Added a revision history.
* Code formatted by ``black``, with a pre-commit hook to enforce this. See the README file for configuration instructions.

Requirements:

* ts_salobj 5.4
* ts_xml 4
* ts_idl 1

v0.4.0
======

Update for ts_xml 4.4 and ts_idl 0.4

Requirements:

* ts_salobj 4
* ts_xml 4.4
* ts_idl 0.4

v0.3.0
======

Update for dds salobj

Requirements:

* ts_salobj 4
* ts_xml
* ts_idl

v0.2.0
======

Updated for changes to the ATPneumatics XML

Requirements:

* ts_xml develop commit 3470860 (2019-02-08) or later
* ts_salobj 3.8

v0.1.0
======

First release

Requirements:

* ts_salobj 3.7
* ts_idl
