Please do contribute! We only have a few simple requirements for diffs and
pull requests.

* `Follow coding guidelines`_
* `Add automated unit tests`_
* `Update documentation`_
* `Add yourself as a contributor`_
* `Open a pull request`_

Follow coding guidelines
------------------------

Logging level usage
'''''''''''''''''''

COT uses logging levels (including the additional intermediate logging levels
provided by the `verboselogs`_ package) as follows:

======= ============================== ========================================
Level   Usage guidelines               Examples
======= ============================== ========================================
ERROR   Something is definitely wrong, * OVF descriptor is not following the
        but COT is able to proceed, at   specification.
        least for the moment. COT may  * User has provided invalid input, but
        raise an exception at some       can retry.
        later point due to this issue. * Expected data is missing.
                                       * Internal logic error in COT that
        If continuing is already known   should never be encountered.
        to be impossible, you should
        raise an exception now instead
        of logging an ERROR message.

WARNING Something potentially wrong,   * COT would have prompted the user to
        or at least risky, happened      provide input or confirm a risky
        that the user should be          operation, but has been instructed to
        informed of.                     run non-interactively.
                                       * COT is having to guess whether a given
        This includes cases where, due   disk drive should be SCSI or IDE as
        to insufficient information      the user didn't specify which when
        provided by the user, COT had    instructing COT to add the drive.
        to make an uncertain choice on * User-provided information was unused,
        its own (or was unable to make   such as providing the device type to
        such a decision but is           set for a device that doesn't exist.
        continuing nonetheless).       * User has instructed COT to configure
                                         hardware settings that appear to be
                                         outside the supported range for the
                                         given platform.

NOTICE  Something noteworthy happened  * COT does not recognize the virtual
        that is not necessarily a        platform described by a given OVF and
        problem, but deserves the        so will be treating it generically.
        user's attention.              * COT is attempting to install a needed
                                         helper application.
        This is the lowest logging     * COT is having to create parts of the
        level enabled by default, so     OVF descriptor from scratch.
        messages generated at and      * COT is replacing a file or disk that
        above this level should be       was previously included in this OVF
        succinct and meaningful to all   with a new one.
        users.

INFO    Status updates about normal    * COT has successfully parsed an OVF or
        operation of the software.       OVA and is ready to operate on it.
                                       * COT is beginning to write the updated
                                         OVF/OVA to disk.

VERBOSE Detailed information of        * Individual task steps of editing
        interest to an expert or very    an OVF.
        curious user.                  * COT's reasoning for making high-level
                                         decisions.

DEBUG   Highly detailed information,   * Information about temporary files and
        probably only useful to a        other internal state of COT itself.
        developer familiar with the    * Individual operations within a complex
        code.                            task.

SPAM    Extremely detailed or          * Data dumps of XML elements and other
        repetitive info that even a      data structures.
        developer will rarely want     * Status updates on tasks that typically
        to see.                          happen many times in a single COT run.
======= ============================== ========================================

Coding style
''''''''''''

We try to keep COT's code base compliant with Python coding standards including
`PEP 8`_ and `PEP 257`_. We use the flake8_ and Pylint_ tools and their
extension packages to verify this as part of our test automation.
To run coding style analysis independently of the other test automation, you
can run ``tox -e flake8,pylint``, or you can install these tools and run them
directly:

::

  cot/$ sudo pip install --upgrade flake8
  cot/$ sudo pip install --upgrade pydocstyle
  cot/$ sudo pip install --upgrade flake8-docstrings
  cot/$ sudo pip install --upgrade pep8-naming
  cot/$ sudo pip install --upgrade mccabe
  cot/$ flake8
  ./COT/ovf/item.py:229:1: C901 'OVFItem.value_replace_wildcards' is too complex (11)
  ./COT/ovf/item.py:603:1: C901 'OVFItem.generate_items' is too complex (11)
  ./COT/ovf/ovf.py:461:1: C901 'OVF.validate_hardware' is too complex (14)

::

  cot/$ sudo pip install --upgrade pylint
  cot/$ pylint COT
  ************* Module COT.ovf.item
  E:331,24: Instance of 'list' has no 'split' member (no-member)
  R:334,16: Redefinition of value type from list to tuple (redefined-variable-type)
  R:603, 4: Too many branches (13/12) (too-many-branches)
  ************* Module COT.ovf.ovf
  C:  1, 0: Too many lines in module (2646/2600) (too-many-lines)
  R:177, 0: Too many public methods (76/74) (too-many-public-methods)

Fix any errors and warnings these tools report, and run again until no errors are reported.

Add automated unit tests
------------------------

Whether adding new functionality or fixing a bug, **please** add appropriate
unit test case(s) under ``COT/tests/`` or  ``COT/<sub-package>/tests/``
(as appropriate) to cover your changes. Your changes **must** pass all existing
and new automated test cases before your code will be accepted.

You can run the COT automated tests under a single Python version by
running ``python ./setup.py test``.

For full testing under all supported versions as well as verifying code
coverage for your tests, you should install tox_ (``pip install tox``) and
coverage_ (``pip install coverage``) then run ``tox`` from the COT directory:

::

  cot/$ tox
  ...
  py27 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  py33 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  py34 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  py35 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  py36 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  pypy runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  flake8 runtests: commands[0] | flake8
  ...
  pylint runtests: commands[0] | pylint COT
  ...
  docs runtests: commands[0] | sphinx-build -W -b html -d ...
  ...
  stats runtests: commands[0] | coverage combine
  stats runtests: commands[1] | coverage report -i
  Name                                 Stmts   Miss Branch BrPart  Cover
  ----------------------------------------------------------------------
  COT/__init__.py                          5      0      0      0   100%
  COT/add_disk.py                        168      3     66      3    97%
  COT/add_file.py                         45      0     12      0   100%
  COT/cli.py                             254     15     95      9    93%
  COT/data_validation.py                 124      2     44      1    98%
  COT/deploy.py                          154      6     62      6    94%
  COT/deploy_esxi.py                     196      0     68      1    99%
  COT/disks/__init__.py                   23      0     10      0   100%
  COT/disks/disk.py                       56      1     20      1    97%
  ...
  COT/vm_description.py                  166      4      4      0    98%
  COT/vm_factory.py                       26      0      4      0   100%
  COT/xml_file.py                        121      3     54      1    98%
  ----------------------------------------------------------------------
  TOTAL                                 5122    114   1908    105    97%
  stats runtests: commands[2] | coverage html -i
  _______________ summary _______________
    setup: commands succeeded
    py27: commands succeeded
    py33: commands succeeded
    py34: commands succeeded
    py35: commands succeeded
    py36: commands succeeded
    pypy: commands succeeded
    flake8: commands succeeded
    pylint: commands succeeded
    docs: commands succeeded
    stats: commands succeeded
    congratulations :)

After running ``tox`` you can check the code coverage details by opening
``htmlcov/index.html`` in a web browser.

Update documentation
--------------------

If you add or change any COT CLI or APIs, or add or remove any external
dependencies, please update the relevant documentation.

Add yourself as a contributor
-----------------------------

If you haven't contributed to COT previously, be sure to add yourself as a
contributor in the ``COPYRIGHT.txt`` file.

Open a pull request
-------------------

COT follows Vincent Driessen's `A successful Git branching model`_. As such,
please submit feature enhancement and non-critical bugfix requests to merge
into the ``develop`` branch rather than ``master``.

.. _verboselogs: https://verboselogs.readthedocs.io/en/latest/
.. _`PEP 8`: https://www.python.org/dev/peps/pep-0008/
.. _`PEP 257`: https://www.python.org/dev/peps/pep-0257/
.. _flake8: http://flake8.readthedocs.org/en/latest/
.. _pep257: http://pep257.readthedocs.org/en/latest/
.. _Pylint: http://www.pylint.org/
.. _tox: http://tox.readthedocs.org/en/latest/
.. _coverage: http://nedbatchelder.com/code/coverage/
.. _`A successful Git branching model`: http://nvie.com/posts/a-successful-git-branching-model/

