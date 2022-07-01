.. py:currentmodule:: lsst.ts.atpneumaticssimulator

.. _lsst.ts.atpneumaticssimulator.version_history:

###############
Version History
###############

v1.1.0
------

Changes:


* Rename command-line scripts to remove ".py" suffix.
* `ATPneumaticsCsc`: call ``super().start()`` at the beginning of the start method.
  This requires ts_salobj 7.1.
* Build with pyproject.toml.
* Modernize the continuous integration ``Jenkinsfile``.

Requirements:

* ts_utils 1
* ts_salobj 7.1
* ts_idl 2
* IDL file for ATPneumatics built from ts_xml 11

v1.0.1
------

Changes:

* tests/test_csc.py test_initial_state: remove obsolete events from the list of initial events to skip.

Requirements:

* ts_utils 1
* ts_salobj 7
* ts_idl 2
* IDL file for ATPneumatics built from ts_xml 11

v1.0.0
------

Changes:

* Update for ts_salobj v7, which is required.
  This also requires ts_xml 11.

Requirements:

* ts_utils 1
* ts_salobj 7
* ts_idl 2
* IDL file for ATPneumatics built from ts_xml 11

v0.6.2
------

* Use ts_utils.
* Add a Jenkinsfile.
* Use pytest-black instead of a custom unit test.
* Modernize unit tests.
* Fix a unit test broken by making ``largeFileObjectAvailable`` a generic event.

Requirements:

* ts_utils 1
* ts_salobj 6
* ts_xml 7
* ts_idl 2

v0.6.1
------

* Use `unittest.IsolatedAsyncioTestCase` instead of the abandoned asynctest package.
* Use pre-commit instead of a custom pre-commit hook; see the README.md for instructions.
* Format the code with black 20.8b1.

Requirements:

* ts_salobj 6
* ts_xml 7
* ts_idl 2

v0.6.0
------

* Modernize the unit tests.
* `ATPneumaticsCsc`: modernize simulation mode handling.
  This requires ts_salobj 6.
* `ATPneumaticsCsc`: add ``version`` class variable, to set the ``cscVersions`` field of the ``softwareVersions`` event.
* Modernize doc/conf.py for documenteer 0.6 and add intersphinx mappings for ts_xml and ts_salobj.

Requirements:

* ts_salobj 6
* ts_xml 7
* ts_idl 2

v0.5.5
------

* Update Jenkinsfile.conda to Jenkins Shared Library 
* Pinned the ts-idl and ts-salobj version in conda recipe
* Change conda package name to ts-atpneumaticssimulator

Requirements:

* ts_salobj 5.11
* ts_xml 4
* ts_idl 1

v0.5.4
------

* Update for compatibility with ts_xml 6.

Requirements:

* ts_salobj 5.11
* ts_xml 4
* ts_idl 1

v0.5.3
------

* Add black to conda test dependencies

Requirements:

* ts_salobj 5.11
* ts_xml 4
* ts_idl 1

v0.5.2
------

* Add ``tests/test_black.py`` to verify that files are formatted with black.
  This requires ts_salobj 5.11 or later.
* Update ``tests/test_csc.py`` to use ``BaseCscTestCase.check_bin_script``.
* Update ``.travis.yml`` to remove ``sudo: false`` to github travis checks pass once again.

Requirements:

* ts_salobj 5.11
* ts_xml 4
* ts_idl 1


v0.5.1
------

* Include conda package build configuration.
* Added a Jenkinsfile to support continuous integration and to build conda packages.

Requirements:

* ts_salobj 5.4
* ts_xml 4
* ts_idl 1

v0.5.0
------

Major changes:

* Modernize CSC unit test to use `lsst.ts.salobj.BaseCscTestCase`.
* Added a revision history.
* Code formatted by ``black``, with a pre-commit hook to enforce this. See the README file for configuration instructions.

Requirements:

* ts_salobj 5.4
* ts_xml 4
* ts_idl 1

v0.4.0
------

Update for ts_xml 4.4 and ts_idl 0.4

Requirements:

* ts_salobj 4
* ts_xml 4.4
* ts_idl 0.4

v0.3.0
------

Update for dds salobj

Requirements:

* ts_salobj 4
* ts_xml
* ts_idl

v0.2.0
------

Updated for changes to the ATPneumatics XML

Requirements:

* ts_xml develop commit 3470860 (2019-02-08) or later
* ts_salobj 3.8

v0.1.0
------

First release

Requirements:

* ts_salobj 3.7
* ts_idl
