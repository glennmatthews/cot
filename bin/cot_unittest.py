#!/bin/bash
#
# cot_unittest.py - Unit test driver for the Common OVF Tool suite
#
# August 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution. No part of COT, including this
# file, may be copied, modified, propagated, or distributed except
# according to the terms contained in the LICENSE.txt file.

''':'
# Find the current working directory and source any helper file provided
dir="$( dirname "$0" )"
if [ -f "$dir/cot_helper.sh" ]; then
  . "$dir/cot_helper.sh"
fi
# Now proceed to find the right python version...
if type python3 >/dev/null 2>/dev/null; then
  exec python3 "$0" "$@"
elif type python2.7 >/dev/null 2>/dev/null; then
  exec python2.7 "$0" "$@"
elif type python-2.7.1 >/dev/null 2>/dev/null; then
  exec python-2.7.1 "$0" "$@"
else
  exec python "$0" "$@"
fi
'''

# You can also invoke test cases with the following command:
# python-2.7.1 -m unittest discover -s COT/tests -p "*.py"

import sys
# We require Python 2.7
if not hasattr(sys, "hexversion") or sys.hexversion < 0x020700f0:
    sys.stderr.write("Your version of python is too old:\n")
    sys.stderr.write(sys.executable)
    sys.stderr.write("\n")
    sys.stderr.write(sys.version)
    sys.stderr.write("\nPython 2.7 or later is required to run COT\n")
    sys.exit(1)
# Different servers may have different Python versions,
# which may generate different compiled bytecode, causing errors
# when a user on a different server tries to load it.
# Hence, we have to take the slight performance hit of never saving the
# compiled bytecode to disk. :-(
sys.dont_write_bytecode = True

import unittest
import os.path
import argparse
import logging


def main():
    parser = argparse.ArgumentParser(description="Common OVF Tool unit tests")

    parser.add_argument('-v', '--verbose', action='count', default=1,
                        help="""Increase verbosity (repeatable)""")

    args = parser.parse_args()

    logging.basicConfig()
    logger = logging.getLogger('cot')
    # Map verbosity to logging level
    log_level = {1: logging.ERROR,
                 2: logging.WARNING,
                 3: logging.INFO}
    # Any verbosity in excess of 3 gets mapped to logging.DEBUG
    logger.setLevel(log_level.get(args.verbose, logging.DEBUG))

    # Discover and load all test cases in the test directory
    tests = unittest.defaultTestLoader.discover('COT.tests', "*.py",
                                                os.path.dirname(
                                                    os.path.dirname(__file__)))
    # Run the tests!
    unittest.TextTestRunner(verbosity=args.verbose, failfast=True).run(tests)

if __name__ == "__main__":
    main()

