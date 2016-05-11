Change Log
==========
All notable changes to the COT project will be documented in this file.
This project adheres to `Semantic Versioning`_.

`1.4.2`_ - 2016-05-11
---------------------

**Added**

- COT now supports ``xorriso`` as another alternative to ``mkisofs`` and ``genisoimage``

**Fixed**

- `#42`_ - ``cot deploy esxi`` error handling behavior needed to be updated for `requests`_ release 2.8.
- `#44`_ - test case failure seen when running `pyVmomi`_ 6.0.0.2016.4.

**Changed**

- Installation document now recommends installation via `pip`_ rather than installing from source.
- `#40`_ - Now uses faster Docker-based infrastructure from `Travis CI`_ for CI builds/tests.

`1.4.1`_ - 2015-09-02
---------------------

**Fixed**

- `#41`_ - symlinks were not dereferenced when writing out to OVA.

`1.4.0`_ - 2015-09-01
---------------------

**Added**

- `#24`_ - ``cot deploy esxi`` now creates serial ports after deployment using
  `pyVmomi`_ library.

  - Serial port connectivity must be specified either via entries in the OVF
    (which can be defined using ``cot edit-hardware ... -S``) or at deployment
    time using the new ``-S`` / ``--serial-connection`` parameter to
    ``cot deploy``.
  - The syntax for serial port connectivity definition is based
    on that of QEMU's ``--serial`` CLI option.
  - Currently only "telnet", "tcp", and "device" connection types are supported.

- `#38`_ - ``cot edit-product`` can now set product and vendor information.
- flake8_ validation now includes pep257_ to validate docstring compliance to
  `PEP 257`_ as well.
- Added changelog file.
- Added ``COT.file_reference`` submodule in support of `#39`_.

**Changed**

- Split ESXi-specific logic out of ``COT.deploy`` module and into new
  ``COT.deploy_esxi`` module.
- UT for ``COT.deploy_esxi`` now requires ``mock`` (standard library in Python 3.x,
  install via pip on Python 2.x).

**Fixed**

- `#39`_ - avoid unnecessary file copies to save time and disk space.

`1.3.3`_ - 2015-07-02
---------------------

**Fixed**

- `#10`_ - When changing network mapping, delete no longer needed networks
- `#31`_ - Added ``--delete-all-other-profiles`` option to
  ``cot edit-hardware``
- `#32`_ - ``cot edit-hardware`` network names can now use wildcards
- `#34`_ - ``cot add-disk`` can now be used to replace a CD-ROM drive with a
  hard disk, or vice versa.


`1.3.2`_ - 2015-04-09
---------------------

**Fixed**

- Adapt to changes to the Travis-CI testing environment.


`1.3.1`_ - 2015-04-09
---------------------

**Fixed**

- `#30`_ - ``cot install-helpers`` can now install ``fatdisk`` and ``vmdktool``
  under Python 3.


`1.3.0`_ - 2015-03-27
---------------------

**Added**

- Installation of helper programs is now provided by a ``cot
  install-helpers`` subcommand rather than a separate script.
- COT now has man pages (``man cot``, ``man cot-edit-hardware``, etc.)
  The man pages are also installed by ``cot install-helpers``.
- Improved documentation of the CLI on readthedocs.org as well.

**Changed**

- Refactored ``COT.helper_tools`` module into ``COT.helpers`` subpackage.
  This package has an API (``COT.helpers.api``) for the rest of COT to
  access it; the helper-specific logic (qemu-img, fatdisk, etc.) is split
  into individual helper modules that are abstracted away by the API.
- Similarly, logic from ``COT.tests.helper_tools`` has been refactored and
  enhanced under ``COT.helpers.tests``.
- Renamed all test code files from "foo.py" to "test_foo.py" to
  facilitate test case discovery.
- CLI help strings are dynamically rendered to ReST when docs are built,
  providing cleaner output for both readthedocs.org and the manpages.

**Removed**

- COT no longer supports Python 3.2.
- ``cot_unittest`` is no more - use ``tox`` or ``unit2 discover`` to run tests.
- As noted above, the installation script ``check_and_install_helpers.py``
  no longer exists - this functionality is now provided by the
  ``COT.install_helpers`` module.


`1.2.4`_ - 2015-03-06
---------------------

**Fixed**

- `#29`_ - ``cot edit-properties`` interactive mode was broken in v1.2.2


`1.2.3`_ - 2015-02-19
---------------------

**Fixed**

- Some documentation fixes for http://cot.readthedocs.org


`1.2.2`_ - 2015-02-19
---------------------

**Added**

- Documentation built with Sphinx and available at http://cot.readthedocs.org

**Changed**

- CLI adapts more intelligently to terminal width (fixes `#28`_)
- Submodules now use Python properties instead of get_value/set_value methods.


`1.2.1`_ - 2015-02-03
---------------------

**Added**

- Now `PEP 8`_ compliant - passes validation by flake8_ code analysis.
- Very preliminary support for OVF 2.x format
- Now uses tox_ for easier test execution and `coverage.py`_ for code coverage
  analysis.
- Code coverage reporting with Coveralls_.

**Changed**

- Now uses colorlog_ instead of ``coloredlogs`` for CLI log colorization, as
  this fits better with COT's logging model.
- Greatly improved unit test structure and code coverage, including tests for
  logging.


`1.2.0`_ - 2015-01-16
---------------------

**Added**

- Greatly improved logging (`#26`_). COT now defaults to logging level INFO,
  which provides relatively brief status updates to the user. You can also
  run with ``--quiet`` to suppress INFO messages and only log WARNING and
  ERROR messages, ``--verbose`` to see VERBOSE messages as well, or ``--debug``
  if you want to really get into the guts of what COT is doing.
- Now integrated with `Travis CI`_ for automated builds and UT under all
  supported Python versions. This should greatly improve the stability of COT
  under less-common Python versions. (`#12`_)

**Changed**

- The CLI for ``cot deploy`` has been revised somewhat based on user feedback.
- A lot of restructuring of the underlying code to make things more modular
  and easier to test in isolation.

**Fixed**

- Various bugfixes for issues specific to Python 2.6 and 3.x - these
  environments should now be fully working again.


`1.1.6`_ - 2015-01-05
---------------------

**Added**

- Added THANKS file recognizing various non-code contributions to COT.

**Fixed**

- Bug fixes for ``cot inject-config`` and ``cot deploy``, including issues
  `#19`_ and `#20`_ and a warning to users about serial ports and ESXi (issue
  eventually to be addressed by fixing `#24`_).
- More graceful handling of Ctrl-C interrupt while COT is running.


`1.1.5`_ - 2014-11-25
---------------------

**Fixed**

- Fixed issue `#17`_ (``cot edit-hardware`` adding NICs makes an OVA that
  vCenter regards as invalid)
- Removed several spurious WARNING messages


`1.1.4`_ - 2014-11-12
---------------------

**Added**

- COT can at least be installed and run under CentOS/Python2.6 now, although
  the automated unit tests will complain about the different XML output that
  2.6 produces.

**Changed**

- Vastly improved installation workflow under Linuxes supporting ``apt-get``
  or ``yum`` - included helper script can automatically install all helper
  programs except ``ovftool``. Fixes `#9`_.

**Fixed**

- Improved ``cot deploy`` handling of config profiles - fixed `#5`_ and `#15`_


`1.1.3`_ - 2014-10-01
---------------------

**Added**

- ``cot edit-hardware`` added ``--nic-names`` option for assigning names to
  each NIC
- ``cot info`` now displays NIC names.

**Fixed**

- Improved installation documentation
- Some improvements to IOS XRv OVA support


`1.1.2`_ - 2014-09-24
---------------------

**Added**

- Take advantage of QEMU 2.1 finally supporting the ``streamOptimized`` VMDK
  sub-format.
- Can now create new hardware items without an existing item of the same type
  (issue `#4`_)

**Changed**

- Clearer documentation and logging messages (issue `#8`_ and others)
- Now uses versioneer_ for automatic version numbering.

**Fixed**

- Fixed several Python 3 compatibility issues (issue `#7`_ and others)


`1.1.1`_ - 2014-08-19
---------------------

**Fixed**

- Minor bug fixes to ``cot deploy esxi``.


`1.1.0`_ - 2014-07-29
---------------------

**Added**

- ``cot deploy esxi`` subcommand by Kevin Keim (@kakeim), which uses ``ovftool``
  to deploy an OVA to an ESXi vCenter server.

**Changed**

- Removed dependencies on ``md5`` / ``md5sum`` / ``shasum`` / ``sha1sum`` in
  favor of Python's ``hashlib`` module.
- Nicer formatting of ``cot info`` output

**Fixed**

- Miscellaneous fixes and code cleanup.


1.0.0 - 2014-06-27
------------------

Initial public release.

.. _#4: https://github.com/glennmatthews/cot/issues/4
.. _#5: https://github.com/glennmatthews/cot/issues/5
.. _#7: https://github.com/glennmatthews/cot/issues/7
.. _#8: https://github.com/glennmatthews/cot/issues/8
.. _#9: https://github.com/glennmatthews/cot/issues/9
.. _#10: https://github.com/glennmatthews/cot/issues/10
.. _#12: https://github.com/glennmatthews/cot/issues/12
.. _#15: https://github.com/glennmatthews/cot/issues/15
.. _#17: https://github.com/glennmatthews/cot/issues/17
.. _#19: https://github.com/glennmatthews/cot/issues/19
.. _#20: https://github.com/glennmatthews/cot/issues/20
.. _#24: https://github.com/glennmatthews/cot/issues/24
.. _#26: https://github.com/glennmatthews/cot/issues/26
.. _#28: https://github.com/glennmatthews/cot/issues/28
.. _#29: https://github.com/glennmatthews/cot/issues/29
.. _#30: https://github.com/glennmatthews/cot/issues/30
.. _#31: https://github.com/glennmatthews/cot/issues/31
.. _#32: https://github.com/glennmatthews/cot/issues/32
.. _#34: https://github.com/glennmatthews/cot/issues/34
.. _#38: https://github.com/glennmatthews/cot/pull/38
.. _#39: https://github.com/glennmatthews/cot/issues/39
.. _#40: https://github.com/glennmatthews/cot/issues/40
.. _#41: https://github.com/glennmatthews/cot/issues/41
.. _#42: https://github.com/glennmatthews/cot/issues/42
.. _#44: https://github.com/glennmatthews/cot/issues/44

.. _Semantic Versioning: http://semver.org/
.. _`PEP 8`: https://www.python.org/dev/peps/pep-0008/
.. _`PEP 257`: https://www.python.org/dev/peps/pep-0257/

.. _pyVmomi: https://pypi.python.org/pypi/pyvmomi/
.. _flake8: http://flake8.readthedocs.org/en/latest/
.. _pep257: https://pypi.python.org/pypi/pep257
.. _requests: http://python-requests.org/
.. _tox: http://tox.readthedocs.org/en/latest/
.. _coverage.py: http://nedbatchelder.com/code/coverage/
.. _Coveralls: https://coveralls.io/r/glennmatthews/cot
.. _colorlog: https://pypi.python.org/pypi/colorlog
.. _Travis CI: https://travis-ci.org/glennmatthews/cot/
.. _versioneer: https://github.com/warner/python-versioneer
.. _pip: https://pip.pypa.io/en/stable/

.. _Unreleased: https://github.com/glennmatthews/cot/compare/master...develop
.. _1.4.2: https://github.com/glennmatthews/cot/compare/v1.4.1...v1.4.2
.. _1.4.1: https://github.com/glennmatthews/cot/compare/v1.4.0...v1.4.1
.. _1.4.0: https://github.com/glennmatthews/cot/compare/v1.3.3...v1.4.0
.. _1.3.3: https://github.com/glennmatthews/cot/compare/v1.3.2...v1.3.3
.. _1.3.2: https://github.com/glennmatthews/cot/compare/v1.3.1...v1.3.2
.. _1.3.1: https://github.com/glennmatthews/cot/compare/v1.3.0...v1.3.1
.. _1.3.0: https://github.com/glennmatthews/cot/compare/v1.2.4...v1.3.0
.. _1.2.4: https://github.com/glennmatthews/cot/compare/v1.2.3...v1.2.4
.. _1.2.3: https://github.com/glennmatthews/cot/compare/v1.2.2...v1.2.3
.. _1.2.2: https://github.com/glennmatthews/cot/compare/v1.2.1...v1.2.2
.. _1.2.1: https://github.com/glennmatthews/cot/compare/v1.2.0...v1.2.1
.. _1.2.0: https://github.com/glennmatthews/cot/compare/v1.1.6...v1.2.0
.. _1.1.6: https://github.com/glennmatthews/cot/compare/v1.1.5...v1.1.6
.. _1.1.5: https://github.com/glennmatthews/cot/compare/v1.1.4...v1.1.5
.. _1.1.4: https://github.com/glennmatthews/cot/compare/v1.1.3...v1.1.4
.. _1.1.3: https://github.com/glennmatthews/cot/compare/v1.1.2...v1.1.3
.. _1.1.2: https://github.com/glennmatthews/cot/compare/v1.1.1...v1.1.2
.. _1.1.1: https://github.com/glennmatthews/cot/compare/v1.1.0...v1.1.1
.. _1.1.0: https://github.com/glennmatthews/cot/compare/v1.0.0...v1.1.0
