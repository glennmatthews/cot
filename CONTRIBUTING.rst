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
`PEP 8`_ and `PEP 257`_. We use the flake8_ and pep257_ tools to verify this
as part of our test automation. To run coding style analysis independently
of the other test automation, you can run ``tox -e flake8``, or you can
install these tools and run ``flake8`` directly:

::

  cot/$ sudo pip install --upgrade flake8
  cot/$ sudo pip install --upgrade pep257
  cot/$ sudo pip install --upgrade flake8-pep257
  cot/$ flake8
  ./COT/tests/ovf.py:180:80: E501 line too long (80 > 79 characters)
  ./COT/tests/ovf.py:184:77: F841 local variable 'ovf' is assigned to but never used
  ./COT/tests/ovf.py:184:80: E501 line too long (80 > 79 characters)
  ./COT/tests/ovf.py:196:40: F841 local variable 'ova' is assigned to but never used
  ./COT/tests/ovf.py:210:75: F841 local variable 'ovf' is assigned to but never used
  ./COT/ovf.py:776:5: E303 too many blank lines (2)

Fix any errors it reports, and run again until no errors are reported.

Add automated unit tests
------------------------

Whether adding new functionality or fixing a bug, **please** add appropriate
unit test case(s) under ``COT/tests/`` to cover your changes. Your changes
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
  py32 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  py33 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  py34 runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  pypy runtests: commands[0] | coverage run --append setup.py test --quiet
  ...
  stats runtests: commands[0] | coverage combine
  stats runtests: commands[1] | coverage report -i
  Name                        Stmts   Miss  Cover
  -----------------------------------------------
  COT/__init__.py                 4      0   100%
  COT/add_disk.py               147      1    99%
  COT/add_file.py                50      0   100%
  COT/cli.py                    143      6    96%
  COT/data_validation.py         69      0   100%
  COT/deploy.py                 142      5    96%
  COT/edit_hardware.py          159      0   100%
  COT/edit_product.py            36      0   100%
  COT/edit_properties.py        104     40    62%
  COT/helper_tools.py           171      3    98%
  COT/info.py                    41      0   100%
  COT/inject_config.py           87      2    98%
  COT/ovf.py                   1586     52    96%
  COT/platforms.py              173      0   100%
  COT/submodule.py               80      2    98%
  COT/ui_shared.py               24      0   100%
  COT/vm_context_manager.py      12      0   100%
  COT/vm_description.py         119      1    99%
  COT/vm_factory.py              25      0   100%
  COT/xml_file.py               112      0   100%
  -----------------------------------------------
  TOTAL                        3284    112    96%
  stats runtests: commands[2] | coverage html -i
  ...
  flake8 runtests: commands[0] | flake8
  _______________ summary _______________
    clean: commands succeeded
    py26: commands succeeded
    py27: commands succeeded
    py33: commands succeeded
    py34: commands succeeded
    pypy: commands succeeded
    flake8: commands succeeded
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
.. _tox: http://tox.readthedocs.org/en/latest/
.. _coverage: http://nedbatchelder.com/code/coverage/
.. _`A successful Git branching model`: http://nvie.com/posts/a-successful-git-branching-model/

