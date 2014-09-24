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

You can run the COT automated tests using the provided `cot_unittest`
script:

```
> ./bin/cot_unittest --help
Usage: python -m unittest discover [options]

Options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose output
  -f, --failfast        Stop on first fail or error
  -c, --catch           Catch ctrl-C and display results so far
  -b, --buffer          Buffer stdout and stderr during tests
  -s START, --start-directory=START
                        Directory to start discovery ('.' default)
  -p PATTERN, --pattern=PATTERN
                        Pattern to match tests ('test*.py' default)
  -t TOP, --top-level-directory=TOP
                        Top level directory of project (defaults to start
                        directory)
```

When run, if all tests pass, you will see output like this:

```
> ./bin/cot_unittest
................................................................................
......................................................
----------------------------------------------------------------------
Ran 134 tests in 32.542s

OK
```

Update README
-------------

If you add or change any COT CLI, or add or remove any external dependencies,
please update the `README.md` appropriately.

Add yourself as a contributor
-----------------------------

If you haven't contributed to COT previously, be sure to add yourself as a
contributor in the `COPYRIGHT.txt` file.
