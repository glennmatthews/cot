Change Log
==========
All notable changes to the COT project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

[Unreleased] - [unreleased]
------------------------
### Added
- Added CHANGELOG.md

[1.3.3] - 2015-07-02
--------------------

### Fixed
- #10 - When changing network mapping, delete no longer needed networks
- #31 - Added `--delete-all-other-profiles` option to `cot edit-hardware`
- #32 - `cot edit-hardware` network names can now use wildcards
- #34 - `cot add-disk` can now be used to replace a CD-ROM drive with a
  hard disk, or vice versa.


[1.3.2] - 2015-04-09
--------------------

### Fixed
- Adapt to changes to the Travis-CI testing environment.


[1.3.1] - 2015-04-09
--------------------

### Fixed
- #30 - `cot install-helpers` can now install `fatdisk` and `vmdktool` with
  Python 3.


[1.3.0] - 2015-03-27
--------------------

### Added
- Installation of helper programs is now provided by a `cot
  install-helpers` subcommand rather than a separate script.
- COT now has man pages (`man cot`, `man cot-edit-hardware`, etc.)
  The man pages are also installed by `cot install-helpers`.
- Improved documentation of the CLI on readthedocs.org as well.

### Changed
- Refactored `COT.helper_tools` module into `COT.helpers` subpackage.
  This package has an API (`COT.helpers.api`) for the rest of COT to
  access it; the helper-specific logic (qemu-img, fatdisk, etc.) is split
  into individual helper modules that are abstracted away by the API.
- Similarly, logic from `COT.tests.helper_tools` has been refactored and
  enhanced under `COT.helpers.tests`.
- Renamed all test code files from "foo.py" to "test_foo.py" to
  facilitate test case discovery.
- CLI help strings are dynamically rendered to ReST when docs are built,
  providing cleaner output for both readthedocs.org and the manpages.

### Removed
- COT no longer supports Python 3.2.
- `cot_unittest` is no more - use `tox` or `unit2 discover` to run tests.
- As noted above, the installation script `check_and_install_helpers.py`
  no longer exists - this functionality is now provided by the
  `COT.install_helpers` module.


[1.2.4] - 2015-03-06
--------------------

### Fixed
- #29 - `cot edit-properties` interactive mode was broken in v1.2.2


[1.2.3] - 2015-02-19
--------------------

### Fixed
- Some documentation fixes for http://cot.readthedocs.org


[1.2.2] - 2015-02-19
--------------------

### Added
- Documentation built with Sphinx and available at http://cot.readthedocs.org

### Changed
- CLI adapts more intelligently to terminal width (fixes #28)
- Submodules now use Python properties instead of get_value/set_value methods.


[1.2.1] - 2015-02-03
--------------------

### Added
- Now [PEP8](https://www.python.org/dev/peps/pep-0008/) compliant - passes
  validation by [`flake8`](http://flake8.readthedocs.org/en/latest/)
  code analysis.
- Very preliminary support for OVF 2.x format
- Now uses [`tox`](http://tox.readthedocs.org/en/latest/) for easier test
  execution and [`coverage.py`](http://nedbatchelder.com/code/coverage/) for
  code coverage analysis.
- Code coverage reporting with
  [Coveralls](https://coveralls.io/r/glennmatthews/cot).

### Changed
- Now uses [`colorlog`](https://pypi.python.org/pypi/colorlog) instead of
  `coloredlogs` for CLI log colorization, as this fits better with COT's
  logging model.
- Greatly improved unit test structure and code coverage, including tests for
  logging.


[1.2.0] - 2015-01-16
--------------------

### Added
- Greatly improved logging (#26). COT now defaults to logging level INFO,
  which provides relatively brief status updates to the user. You can also
  run with `--quiet` to suppress INFO messages and only log WARNING and
  ERROR messages, `--verbose` to see VERBOSE messages as well, or `--debug`
  if you want to really get into the guts of what COT is doing.
- Now integrated with [Travis CI](https://travis-ci.org/glennmatthews/cot/)
  for automated builds and UT under all supported Python versions. This should
  greatly improve the stability of COT under less-common Python versions. (#12)

### Changed
- The CLI for `cot deploy` has been revised somewhat based on user feedback.
- A lot of restructuring of the underlying code to make things more modular
  and easier to test in isolation.

### Fixed
- Various bugfixes for issues specific to Python 2.6 and 3.x - these
  environments should now be fully working again.


[1.1.6] - 2015-01-05
--------------------

### Added
- Added THANKS file recognizing various non-code contributions to COT.

### Fixed
- Bug fixes for `cot inject-config` and `cot deploy`, including issues #19
  and #20 and a warning to users about serial ports and ESXi (issue
  eventually to be addressed by fixing #24).
- More graceful handling of Ctrl-C interrupt while COT is running.


[1.1.5] - 2014-11-25
--------------------

### Fixed
- Fixed issue #17 (`cot edit-hardware` adding NICs makes an OVA that vCenter
  regards as invalid)
- Removed several spurious WARNING messages


[1.1.4] - 2014-11-12
--------------------

### Added
- COT can at least be installed and run under CentOS/Python2.6 now, although
  the automated unit tests will complain about the different XML output that
  2.6 produces.

### Changed
- Vastly improved installation workflow under Linuxes supporting `apt-get`
  or `yum` - included helper script can automatically install all helper
  programs except `ovftool`. Fixes #9.

### Fixed
- Improved `cot deploy` handling of config profiles - fixed #5 and #15


[1.1.3] - 2014-10-01
--------------------

### Added
- `cot edit-hardware` added `--nic-names` option for assigning names to
  each NIC
- `cot info` now displays NIC names.

### Fixed
- Improved installation documentation
- Some improvements to IOS XRv OVA support


[1.1.2] - 2014-09-24
--------------------

### Added
- Take advantage of QEMU 2.1 finally supporting the `streamOptimized` VMDK
  sub-format.
- Can now create new hardware items without an existing item of the same type
  (issue #4)

### Changed
- Clearer documentation and logging messages (issue #8 and others)
- Now uses [versioneer](https://github.com/warner/python-versioneer) for
  automatic version numbering.

### Fixed
- Fixed several Python 3 compatibility issues (issue #7 and others)


[1.1.1] - 2014-08-19
--------------------

### Fixed
- Minor bug fixes to `cot deploy esxi`.


[1.1.0] - 2014-07-29
--------------------

### Added
- `cot deploy esxi` subcommand by Kevin Keim (@kakeim), which uses `ovftool`
  to deploy an OVA to an ESXi vCenter server.

### Changed
- Removed dependencies on `md5`/`md5sum`/`shasum`/`sha1sum` in favor of
  Python's `hashlib` module.
- Nicer formatting of `cot info` output

### Fixed
- Miscellaneous fixes and code cleanup.


1.0.0 - 2014-06-27
------------------

Initial public release.

[unreleased]: https://github.com/glennmatthews/cot/compare/v1.3.3...develop
[1.3.3]: https://github.com/glennmatthews/cot/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/glennmatthews/cot/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/glennmatthews/cot/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/glennmatthews/cot/compare/v1.2.4...v1.3.0
[1.2.4]: https://github.com/glennmatthews/cot/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/glennmatthews/cot/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/glennmatthews/cot/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/glennmatthews/cot/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/glennmatthews/cot/compare/v1.1.6...v1.2.0
[1.1.6]: https://github.com/glennmatthews/cot/compare/v1.1.5...v1.1.6
[1.1.5]: https://github.com/glennmatthews/cot/compare/v1.1.4...v1.1.5
[1.1.4]: https://github.com/glennmatthews/cot/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/glennmatthews/cot/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/glennmatthews/cot/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/glennmatthews/cot/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/glennmatthews/cot/compare/v1.0.0...v1.1.0
