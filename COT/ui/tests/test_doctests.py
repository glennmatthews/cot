#!/usr/bin/env python
#
# test_doctests.py - test runner for COT doctests
#
# July 2016, Glenn F. Matthews
# Copyright (c) 2016-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Test runner for COT doctest tests."""

import logging
from logging import NullHandler

from doctest import DocTestSuite
from unittest import TestSuite

logging.getLogger('COT').addHandler(NullHandler())


def load_tests(*_):
    """Load doctests as unittest test suite.

    For the parameters, see :mod:`unittest`. The parameters are unused here.
    """
    suite = TestSuite()
    suite.addTests(DocTestSuite('COT.ui.cli'))
    return suite
