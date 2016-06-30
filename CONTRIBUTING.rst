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

  ERROR
    Something is wrong (such as a violation of the OVF specification)
    but COT was able to attempt to recover. If recovery is not possible,
    you should raise an ``Error`` of appropriate type instead of logging
    an ERROR message.
  WARNING
    Something unexpected or risky happened that the user needs a
    heads-up about. This includes cases where the software had to make
    an uncertain choice on its own due to lack of information from the
    user.
  INFO
    Important status updates about normal operation of the software.
    As this is the lowest logging level enabled by default, you should
    keep the logs generated at this level relatively brief but
    meaningful.
  VERBOSE
    Detailed information of interest to an advanced or inquisitive user.
  DEBUG
    Highly detailed information only useful to a developer familiar with
    the code.

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
unit test case(s) under ``COT/tests/``, ``COT/helpers/tests/``, or
``COT/ovf/tests`` (as appropriate) to cover your changes. Your changes
**must** pass all existing and new automated test cases before your code
will be accepted.

You can run the COT automated tests under a single Python version by
running ``python ./setup.py test``.

For full testing under all supported versions as well as verifying code
coverage for your tests, you should install tox_ (``pip install tox``) and
coverage_ (``pip install coverage``) then run ``tox`` from the COT directory:

::

  cot/$ tox
  ...
  py26 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  py27 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  py33 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  py34 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  pypy runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  flake8 runtests: commands[0] | flake8 --verbose
  ...
  pylint runtests: commands[0] | pylint COT
  ...
  docs runtests: commands[0] | sphinx-build -W -b html -d ...
  ...
  stats runtests: commands[0] | coverage combine
  stats runtests: commands[1] | coverage report -i
  Name                        Stmts   Miss  Cover
  -----------------------------------------------
  COT/__init__.py                 5      0   100%
  COT/add_disk.py               166      1    99%
  COT/add_file.py                45      0   100%
  COT/cli.py                    252     15    94%
  COT/data_validation.py         88      0   100%
  COT/deploy.py                 148      4    97%
  COT/deploy_esxi.py            201     28    86%
  COT/edit_hardware.py          273      2    99%
  ...
  COT/vm_description.py         168      4    98%
  COT/vm_factory.py              26      0   100%
  COT/xml_file.py               120      0   100%
  -----------------------------------------------
  TOTAL                        4692    136    97%
  stats runtests: commands[2] | coverage html -i
  _______________ summary _______________
    setup: commands succeeded
    py26: commands succeeded
    py27: commands succeeded
    py33: commands succeeded
    py34: commands succeeded
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

.. _`PEP 8`: https://www.python.org/dev/peps/pep-0008/
.. _`PEP 257`: https://www.python.org/dev/peps/pep-0257/
.. _flake8: http://flake8.readthedocs.org/en/latest/
.. _pep257: http://pep257.readthedocs.org/en/latest/
.. _Pylint: http://www.pylint.org/
.. _tox: http://tox.readthedocs.org/en/latest/
.. _coverage: http://nedbatchelder.com/code/coverage/
.. _`A successful Git branching model`: http://nvie.com/posts/a-successful-git-branching-model/

