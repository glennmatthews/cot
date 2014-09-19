Contributing to COT
===================

Please do! We only have a few simple requirements for diffs and pull requests.

* [Add automated unit tests](#add-automated-unit-tests)
* [Update README](#update-readme)
* [Add yourself as a contributor](#add-yourself-as-a-contributor)

Add automated unit tests
------------------------

Whether adding new functionality or fixing a bug, **please** add appropriate
unit test case(s) under `COT/tests/` to cover your changes. Your changes
**must** pass all existing and new automated test cases before your code
will be accepted.

You can run the COT automated tests using the provided `cot_unittest.py`
script:

    > ./bin/cot_unittest.py --help
    usage: cot_unittest.py [-h] [-v]

    Common OVF Tool unit tests

    optional arguments:
      -h, --help     show this help message and exit
      -v, --verbose  Increase verbosity (repeatable)

When run, if all tests pass, you will see output like this::

    > ./bin/cot_unittest.py
    .........................................................................................................................
    ----------------------------------------------------------------------
    Ran 123 tests in 38.184s

    OK

Update README
-------------

If you add or change any COT CLI, or add or remove any external dependencies,
please update the `README.md` appropriately.

Add yourself as a contributor
-----------------------------

If you haven't contributed to COT previously, be sure to add yourself as a
contributor in the `COPYRIGHT.txt` file.
