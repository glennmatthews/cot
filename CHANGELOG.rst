Change Log
==========
All notable changes to the COT project will be documented in this file.
This project adheres to `Semantic Versioning`_.

`2.2.1`_ - 2019-12-04
---------------------

**Added**

- COT now officially supports Python 3.7.

`2.2.0`_ - 2019-02-18
---------------------

**Added**

- COT now recognizes and validates the Cisco C9800-CL platform.

**Removed**

- Discontinued support for Python 3.3 as it has been retired since 2017.

`2.1.0`_ - 2018-01-29
---------------------

**Fixed**

- The ``bin/cot`` helper script in this repository (not the script installed
  when installing COT normally) has had some ``$PATH`` issues fixed.
- ``cot add-disk ... --controller`` now accepts ``sata`` as an additional
  option (`#72`_).

`2.0.5`_ - 2017-11-30
---------------------

**Fixed**

- Error in previous release due to COT using a user-specified relative file
  path in ``FileReference.create`` which implicitly assumed absolute paths.

  - Now correctly fixes up the path before constructing this ``FileReference``.
  - To prevent similar errors in the future, if a ``FileReference`` is
    constructed with a non-absolute path, COT will log a warning and attempt
    to fix the path at that point.

`2.0.4`_ - 2017-11-30
---------------------

**Fixed**

- COT now ensures that cloned Items have a higher InstanceID than the Item
  they were cloned from, avoiding unexpected out-of-order behavior (`#70`_).
- COT now produces valid manifests for OVF 2.x files (which use SHA256
  instead of SHA1 as in OVF 0.x and 1.x).

**Added**

- Official support for pypy3. (COT has already been usable under pypy3, but
  now it's actually part of our tests.)
- COT checks the manifest when loading an OVF/OVA and warns if any
  checksum mismatches are seen.
- ``FileReference`` class as superclass of ``FileInTAR`` and ``FileOnDisk``.

**Changed**

- Refactored how man page builds are triggered so that Sphinx is no longer a
  mandatory pre-requisite for building COT. This helps us to avoid breaking
  Travis-CI tests when a new version of Sphinx comes out that doesn't support
  older Python versions like 3.3.
- Replaced ``add_disk.guess_drive_type_from_extension`` with
  ``DiskRepresentation.predicted_drive_type``.

`2.0.3`_ - 2017-04-03
---------------------

**Fixed**

- Fixed issue where UnboundLocalError would be raised during COT's
  attempt to clean up after a qemu-img error occurring while trying to
  convert a disk to VMDK (`#67`_).
- Fixed incorrect invocation of 'sudo mkdir' on Mac OS X.

`2.0.2`_ - 2017-03-20
---------------------

**Fixed**

- Path normalization of output file resulted in COT failing to detect the
  case of self-overwriting an OVA, resulting in file corruption (`#66`_).
  Improved detection of self-overwriting cases including relative vs.
  absolute paths, symlinks, and hardlinks.

`2.0.1`_ - 2017-03-17
---------------------

**Fixed**

- One unit test case,
  COT.helpers.tests.test_helper.HelperGenericTest.test_download_and_expand_tgz,
  was failing after 2.0.0 was released, due to its assumptions about the
  contents of the master repo on GitHub no longer being valid. Fixed now.

`2.0.0`_ - 2017-03-17
---------------------

**Fixed**

- Fixed a case that could result in a RuntimeError being thrown when using
  ``cot edit-hardware`` to simultaneously create NICs and define a new
  configuration profile (`#64`_).
- Update minimum QEMU version preferred for creation of streamOptimized VMDK
  files from 2.1.0 to 2.5.1, due to an incompatibility with VMware in VMDKs
  produced by versions prior to 2.5.1 (`#65`_).

  - If ``vmdktool`` is not installed, but QEMU 2.1.0-2.5.0 is, then COT will
    fall back to usinq ``qemu-img``, but will warn of this potential
    incompatibility with ESXi.

- When ``cot info`` is invoked with multiple files as input, an error in
  loading one file will no longer cause the entire command to abort;
  COT will now log an error about the offending file and continue to the next.

**Added**

- COT commands now check the available disk space in the temporary working
  directory against the temporary storage space the command estimates it
  will require, and if there is likely to be a problem, warns the user
  before continuing. (`#63`_)
- Additionally COT commands that write out an updated OVF/OVA now check the
  available disk space in the requested output location against the VM's
  predicted output size, and if there is likely to be a problem, warns the
  user before continuing.
- ``Helper`` classes can now opt to cache their output to avoid repeatedly
  re-running the same command. Currently enabled for ``qemu-img info ...``
  and ``isoinfo ...`` commands. (`#62`_)
- New modules and APIs in support of the above:

  - ``Command.working_dir_disk_space_required()`` instance method, to ask a
    command to estimate how much temporary storage it will require. This
    method is now automatically called from Command unit tests to validate
    its accuracy.
  - ``VMDescription.predicted_output_size()`` instance method, to ask a VM
    to estimate how much disk space it will require when written out.
  - ``COT.utilities`` module with functions ``available_bytes_at_path`` and
    ``tar_entry_size``.

**Removed**

- Discontinued support for Python 2.6 as it has been retired since 2013.
- Removed ``cot --debug`` alias for ``cot --verbose --verbose`` as it is
  no longer correct after increased granularity of logging options,
  as described below.

**Changed**

- With ``cot edit-hardware``, the platform hardware validation is no longer
  a hard limit. Instead, if a value appears to be invalid, the user will be
  warned about the validation failure and given the option to continue or
  abort (`#61`_).
  ``cot --force ...``, as usual, can be used to auto-continue without prompting.
- More granular logging levels (thanks to `verboselogs`_; COT now requires
  version 1.6 of this package) and more self-consistency in message logging.
- Revised format of log messages generated by COT.
- Lots of API changes:

  - All commands ('submodules') are now grouped as a sub-package
    under ``COT.commands``. Most classes in this package have been renamed.
  - Moved ``COT.ovf`` package to be a sub-package under ``COT.vm_description``.
  - Moved UI and CLI classes into a ``COT.ui`` sub-package.
  - Moved the ``to_string`` function from ``COT.data_validation`` to
    ``COT.utilities``.
  - Function ``COT.deploy_esxi.get_object_from_connection`` is now method
    ``PyVmomiVMReconfigSpec.lookup_object``.
  - Function ``COT.cli.formatter`` is now class
    ``COT.ui.cli.CLILoggingFormatter``.
  - The functionality of classes ``VMContextManager`` and ``VMFactory`` has
    been rolled into the core ``VMDescription`` class.
  - COT.disks module:

    - Function ``create_disk`` is now split into class methods
      ``DiskRepresentation.for_new_file`` (creates the disk file and returns a
      corresponding ``DiskRepresentation`` instance) and
      ``DiskRepresentation.create_file`` (creates disk file only).
    - Function ``convert_disk`` is now class method
      ``DiskRepresentation.convert_to``
    - Function ``disk_representation_from_file`` is now
      class method ``DiskRepresentation.from_file``
    - The ``DiskRepresentation`` constructor now only takes the path to a file
      as input - if you want to create a new file, use
      ``DiskRepresentation.for_new_file`` instead of calling the
      constructor directly.

  - COT.helpers module:

    - Static method ``Helper.cp`` has been renamed to ``Helper.copy_file``.

  - COT.ovf module:

    - ``COT.ovf.ovf.byte_string`` has been moved and renamed to
      ``COT.utilities.pretty_bytes``.
    - ``COT.ovf.ovf.byte_count`` has been moved and renamed to
      ``COT.vm_description.ovf.utilities.programmatic_bytes_to_int``.
    - ``COT.ovf.ovf.factor_bytes`` has been moved and renamed to
      ``COT.vm_description.ovf.utilities.int_bytes_to_programmatic_units``.
    - ``OVF.validate_and_update_file_references`` and
      ``OVF.validate_and_update_networks`` have been moved to private
      functions and are no longer part of the public API of the OVF class.
    - ``Hardware.update_existing_item_count_per_profile`` has been
      moved to a private method.

  - COT.platforms module:

    - Class ``GenericPlatform`` is now ``Platform``.
    - Function ``platform_from_product_class`` is now class method
      ``Platform.for_product_string`` and returns an instance
      of a ``Platform`` class rather than the class object itself.
    - Most ``Platform`` APIs are now instance methods instead of
      class methods.
    - Function ``COT.platforms.is_known_product_class`` has been removed.

`1.9.1`_ - 2017-02-21
---------------------

**Changed**

- Removed 32 GiB memory limitation on Cisco IOS XRv 9000 platform.

`1.9.0`_ - 2017-02-13
---------------------

**Added**

- Support for Python 3.6
- Support for `brew` package manager (`#55`_).
- Support for Cisco Nexus 9000v (NX-OSv 9000) platform (`#60`_).

**Fixed**

- Improved messaging when COT is unable to install a helper program (`#57`_).

`1.8.2`_ - 2017-01-18
---------------------

**Fixed**

- Issue (`#58`_) where various multi-value CLI options for the
  ``edit-hardware`` and ``inject-config`` commands did not append properly.
- Issue in which explicitly specified NIC names were being overwritten by
  names auto-derived from network names when attempting to set both NIC name
  and network names in a single ``cot edit-hardware`` call.
- ``cot edit-properties`` again accepts property values containing the characters
  ``+`` and ``=`` (`#59`_).

**Added**

- COT can now detect the presence of an .ovf file in a TAR archive even if
  the archive is not named ``*.ova*`` and even if the .ovf file is not the first
  file in the archive as specified by the OVF specification. This allows
  (read-only at present) handling of VirtualBox Vagrant .box files,
  which are approximately equivalent to non-standards-compliant OVAs.

`1.8.1`_ - 2016-11-12
---------------------

**Fixed**

- Under Python versions older than 2.7.9, explicitly require ``pyOpenSSL`` and
  ``ndg-httpsclient`` to avoid issues like
  ``hostname 'people.freebsd.org' doesn't match 'wfe0.ysv.freebsd.org'``
  when installing vmdktool.

`1.8.0`_ - 2016-11-08
---------------------

**Fixed**

- TypeError in ``find_item`` method (`#54`_).
- ``cot inject-config`` correctly handles OVAs with multiple empty CD-ROM
  drives to choose amongst (`#54`_ also).
- Cisco CSR1000v platform now supports 8 CPUs as a valid option.

**Added**

- ``cot inject-config --extra-files`` parameter (`#53`_).
- Helper class for ``isoinfo`` (a companion to ``mkisofs``).
- Added glossary of terms to COT documentation.
- Inline documentation (docstrings) are now validated using the `Pylint`_
  `docparams`_ extension.

**Changed**

- Refactored the monolithic ``COT/platforms.py`` file into a proper submodule.
- :func:`~COT.helpers.mkisofs.MkIsoFs.create_iso` now adds Rock Ridge extensions
  by default.
- Refactored :mod:`COT.helpers` into two modules - :mod:`COT.helpers`
  (now just for handling helper programs such as ``apt-get`` and ``mkisofs``)
  and :mod:`COT.disks` (which uses the helpers to handle ISO/VMDK/QCOW2/RAW
  image files).
- Inline documentation (docstrings) have been converted to "`Google style`_"
  for better readability in the code. Sphinx rendering of documentation
  (for readthedocs.org, etc) now makes use of the `napoleon`_ extension to
  handle this style.

**Removed**

- :func:`get_checksum` is no longer part of the :mod:`COT.helpers` API.
  (It's now the method :func:`~COT.data_validation.file_checksum` in
  ``COT.data_validation``, where it really belonged from the start).
- :func:`download_and_expand` is no longer part of the :mod:`COT.helpers`
  public API. (It's now the static method
  :func:`~COT.helpers.helper.Helper.download_and_expand_tgz`
  on class :class:`~COT.helpers.helper.Helper`.)

`1.7.4`_ - 2016-09-21
---------------------

Newer versions of Sphinx have dropped support for Python 2.6 and 3.3, so
I have updated COT's installation requirements to use older Sphinx versions
under these Python versions.

`1.7.3`_ - 2016-09-06
---------------------

**Added**

- When adding NICs to an OVF, if no ``-nic-networks`` are specified,
  ``cot edit-hardware`` will now try to infer sequential naming of the
  Network elements and if successful, offer to create additional Networks
  as appropriate. (`#18`_)

`1.7.2`_ - 2016-08-17
---------------------

**Fixed**

- Issue `#52`_ - OVFItemDataError raised when adding NICs to CSR1000V OVA,
  or more generally when cloning an OVFItem whose ElementName references
  its Connection.

`1.7.1`_ - 2016-08-12
---------------------

**Fixed**

- ``cot deploy ... --serial-connection`` will create additional serial ports
  beyond those defined in the OVF, if requested. Previously it would ask the
  user for confirmation but not actually do anything about it. (`#51`_)

`1.7.0`_ - 2016-08-05
---------------------

**Added**

- Support for Python 3.5
- Enhancements to ``cot edit-properties`` (`#50`_):

  - Added ``--user-configurable`` option to set whether created/updated
    properties are marked as user-configurable in the OVF.
  - Added ``--labels`` and ``--descriptions`` options to set/update the
    labels and descriptions associated with properties.
  - It's now valid to set no default value for a property by
    omitting the ``=value``, as in ``-p property-with-no-value``, as well as
    the existing ``-p property-with-empty-value=`` syntax to set
    an empty string as the value.
  - Users can now optionally specify the property type to enforce for each
    property by using the delimiter ``+type``, as in ``-p key=1+boolean``.

**Changed**

- Switched from statement coverage to branch coverage for better test analysis.
- Moved from `Coveralls`_ to `Codecov`_ for test coverage tracking, since
  Coveralls does not support branch coverage reporting.

**Fixed**

- When ``cot edit-hardware`` is used to create new NICs in an OVF that
  previously had none, and the user does not specify any corresponding Network
  entries, automatically create a 'VM Network' entry, because all NICs must
  be mapped to Networks for a valid OVF descriptor.

`1.6.1`_ - 2016-07-07
---------------------

**Fixed**

- ``ValueMismatchError`` exceptions are properly caught by the CLI wrapper
  so as to result in a graceful exit rather than a stack trace.
- ``cot remove-file`` now errors if the user specifies both file-id and
  file-path, one of which matches a file in the OVF, but the other does not
  match this or any other file.
- Better handling of exceptions and usage of ``sudo`` when installing helpers.
- Manual pages are now correctly included in the distribution. Oops!


`1.6.0`_ - 2016-06-30
---------------------

**Added**

- ``cot edit-product --product-class`` option, to set or change the
  product class identifier (such as ``com.cisco.csr1000v``).
- Enabled additional code quality validation with `Pylint`_, `pep8-naming`_,
  and `mccabe`_ (`#49`_).

**Changed**

- Lots of refactoring to reduce code complexity as measured by `Pylint`_
  and `mccabe`_.

**Fixed**

- COT now recognizes ``AllocationUnits`` values like ``megabytes``.
- COT no longer ignores the ``AllocationUnits`` value given for RAM.
- :func:`COT.ovf.byte_string` now properly uses binary units (``KiB`` rather
  than ``kB``, etc.)

`1.5.2`_ - 2016-06-17
---------------------

**Changed**

- Development requirement changes: The package `pep8`_ has been renamed to
  `pycodestyle`_, and `pep257`_ has been renamed to `pydocstyle`_. Updated
  configuration and documentation to reflect these changes. Also,
  `flake8-pep257`_ does not presently handle these changes, so replaced it
  as a dependency with the more up-to-date `flake8-docstrings`_ package.

`1.5.1`_ - 2016-06-07
---------------------

**Added**

- ``cot edit-hardware --network-descriptions`` option, to specify the
  descriptive string(s) associated with each network definition.

**Fixed**

- `#48`_ - NIC type not set when adding NICs to an OVF that had none before.
- When updating NIC network mapping, COT now also updates any Description
  that references the network mapping.

`1.5.0`_ - 2016-06-06
---------------------

**Added**

- `#47`_ - Added ``cot remove-file`` subcommand.
- `#43`_ - add ``cot edit-properties --transport`` option to set environment
  transport type(s) - iso, VMWare Tools, etc.

  - ``cot info`` now has a new "Environment" section that displays the
    transport type

- `#45`_ - support for multiple values for ``--nic-types``, ``--ide-subtypes``,
  and ``--scsi-subtypes`` in ``cot edit-hardware``.
- COT now recognizes the Cisco IOS XRv 9000 platform identifier
  ``com.cisco.ios-xrv9000``.
- `#21`_ - subcommand aliases (Python 3.x only):

  - ``cot edit-product`` aliases: ``cot set-product``, ``cot set-version``
  - ``cot edit-properties`` aliases: ``cot set-properties``,
    ``cot edit-environment``, ``cot set-environment``
  - ``cot info`` alias: ``cot describe``
  - ``cot inject-config`` alias: ``cot add-bootstrap``
  - ``cot remove-file`` alias: ``cot delete-file``

- Support for tab-completion of CLI parameters using `argcomplete`_.

**Changed**

- ``cot edit-hardware`` options ``--nic-types``, ``--ide-subtypes``, and
  ``--scsi-subtypes`` are now validated and canonicalized by COT, meaning that:

  - ``cot edit-hardware --nic-type virtio-net-pci`` is now a valid command and
    will correctly create an OVF with ``ResourceSubType`` ``virtio``
    (not ``virtio-net-pci``)
  - ``cot edit-hardware --ide-subtype foobar`` will now fail with an error

- ``cot info`` is now more self-consistent in how it displays property keys.
  They are now always wrapped in ``<`` ``>``, whereas previously this was
  only sometimes the case.
- ``cot info --verbose`` now displays file and disk ID strings under the
  "Files and Disks" section.

`1.4.2`_ - 2016-05-11
---------------------

**Added**

- COT now supports ``xorriso`` as another alternative to ``mkisofs`` and
  ``genisoimage``

**Fixed**

- `#42`_ - ``cot deploy esxi`` error handling behavior needed to be updated
  for `requests`_ release 2.8.
- `#44`_ - test case failure seen when running `pyVmomi`_ 6.0.0.2016.4.

**Changed**

- Installation document now recommends installation via `pip`_ rather than
  installing from source.
- `#40`_ - Now uses faster Docker-based infrastructure from `Travis CI`_ for
  CI builds/tests.

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
.. _#18: https://github.com/glennmatthews/cot/issues/18
.. _#19: https://github.com/glennmatthews/cot/issues/19
.. _#20: https://github.com/glennmatthews/cot/issues/20
.. _#21: https://github.com/glennmatthews/cot/issues/21
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
.. _#43: https://github.com/glennmatthews/cot/issues/43
.. _#44: https://github.com/glennmatthews/cot/issues/44
.. _#45: https://github.com/glennmatthews/cot/issues/45
.. _#47: https://github.com/glennmatthews/cot/issues/47
.. _#48: https://github.com/glennmatthews/cot/issues/48
.. _#49: https://github.com/glennmatthews/cot/issues/49
.. _#50: https://github.com/glennmatthews/cot/issues/50
.. _#51: https://github.com/glennmatthews/cot/issues/51
.. _#52: https://github.com/glennmatthews/cot/issues/52
.. _#53: https://github.com/glennmatthews/cot/issues/53
.. _#54: https://github.com/glennmatthews/cot/issues/54
.. _#55: https://github.com/glennmatthews/cot/issues/55
.. _#57: https://github.com/glennmatthews/cot/issues/57
.. _#58: https://github.com/glennmatthews/cot/issues/58
.. _#59: https://github.com/glennmatthews/cot/issues/59
.. _#60: https://github.com/glennmatthews/cot/issues/60
.. _#61: https://github.com/glennmatthews/cot/issues/61
.. _#62: https://github.com/glennmatthews/cot/issues/62
.. _#63: https://github.com/glennmatthews/cot/issues/63
.. _#64: https://github.com/glennmatthews/cot/issues/64
.. _#65: https://github.com/glennmatthews/cot/issues/65
.. _#66: https://github.com/glennmatthews/cot/issues/66
.. _#67: https://github.com/glennmatthews/cot/issues/67
.. _#70: https://github.com/glennmatthews/cot/issues/70
.. _#72: https://github.com/glennmatthews/cot/issues/72

.. _Semantic Versioning: http://semver.org/
.. _`PEP 8`: https://www.python.org/dev/peps/pep-0008/
.. _`PEP 257`: https://www.python.org/dev/peps/pep-0257/

.. _pyVmomi: https://pypi.python.org/pypi/pyvmomi/
.. _flake8: http://flake8.readthedocs.org/en/latest/
.. _pep8: https://pypi.python.org/pypi/pep8
.. _pep257: https://pypi.python.org/pypi/pep257
.. _requests: http://python-requests.org/
.. _tox: http://tox.readthedocs.org/en/latest/
.. _coverage.py: http://nedbatchelder.com/code/coverage/
.. _Coveralls: https://coveralls.io/r/glennmatthews/cot
.. _colorlog: https://pypi.python.org/pypi/colorlog
.. _Travis CI: https://travis-ci.org/glennmatthews/cot/
.. _versioneer: https://github.com/warner/python-versioneer
.. _pip: https://pip.pypa.io/en/stable/
.. _argcomplete: https://argcomplete.readthedocs.io/en/latest/
.. _`flake8-pep257`: https://pypi.python.org/pypi/flake8-pep257
.. _pycodestyle: https://pypi.python.org/pypi/pycodestyle
.. _pydocstyle: https://pypi.python.org/pypi/pydocstyle
.. _`flake8-docstrings`: https://pypi.python.org/pypi/flake8-docstrings
.. _Pylint: https://www.pylint.org/
.. _docparams: https://docs.pylint.org/en/1.6.0/extensions.html#parameter-documentation-checker
.. _`pep8-naming`: https://pypi.python.org/pypi/pep8-naming
.. _mccabe: https://pypi.python.org/pypi/mccabe
.. _Codecov: https://codecov.io
.. _`Google style`: https://google.github.io/styleguide/pyguide.html?showone=Comments#Comments
.. _napoleon: http://www.sphinx-doc.org/en/latest/ext/napoleon.html
.. _verboselogs: https://verboselogs.readthedocs.io/en/latest/

.. _Unreleased: https://github.com/glennmatthews/cot/compare/master...develop
.. _2.2.1: https://github.com/glennmatthews/cot/compare/v2.2.0...v2.2.1
.. _2.2.0: https://github.com/glennmatthews/cot/compare/v2.1.0...v2.2.0
.. _2.1.0: https://github.com/glennmatthews/cot/compare/v2.0.5...v2.1.0
.. _2.0.5: https://github.com/glennmatthews/cot/compare/v2.0.4...v2.0.5
.. _2.0.4: https://github.com/glennmatthews/cot/compare/v2.0.3...v2.0.4
.. _2.0.3: https://github.com/glennmatthews/cot/compare/v2.0.2...v2.0.3
.. _2.0.2: https://github.com/glennmatthews/cot/compare/v2.0.1...v2.0.2
.. _2.0.1: https://github.com/glennmatthews/cot/compare/v2.0.0...v2.0.1
.. _2.0.0: https://github.com/glennmatthews/cot/compare/v1.9.1...v2.0.0
.. _1.9.1: https://github.com/glennmatthews/cot/compare/v1.9.0...v1.9.1
.. _1.9.0: https://github.com/glennmatthews/cot/compare/v1.8.2...v1.9.0
.. _1.8.2: https://github.com/glennmatthews/cot/compare/v1.8.1...v1.8.2
.. _1.8.1: https://github.com/glennmatthews/cot/compare/v1.8.0...v1.8.1
.. _1.8.0: https://github.com/glennmatthews/cot/compare/v1.7.4...v1.8.0
.. _1.7.4: https://github.com/glennmatthews/cot/compare/v1.7.3...v1.7.4
.. _1.7.3: https://github.com/glennmatthews/cot/compare/v1.7.2...v1.7.3
.. _1.7.2: https://github.com/glennmatthews/cot/compare/v1.7.1...v1.7.2
.. _1.7.1: https://github.com/glennmatthews/cot/compare/v1.7.0...v1.7.1
.. _1.7.0: https://github.com/glennmatthews/cot/compare/v1.6.1...v1.7.0
.. _1.6.1: https://github.com/glennmatthews/cot/compare/v1.6.0...v1.6.1
.. _1.6.0: https://github.com/glennmatthews/cot/compare/v1.5.2...v1.6.0
.. _1.5.2: https://github.com/glennmatthews/cot/compare/v1.5.1...v1.5.2
.. _1.5.1: https://github.com/glennmatthews/cot/compare/v1.5.0...v1.5.1
.. _1.5.0: https://github.com/glennmatthews/cot/compare/v1.4.2...v1.5.0
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
