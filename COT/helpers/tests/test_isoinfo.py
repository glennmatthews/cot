#!/usr/bin/env python
# coding=utf-8
#
# March 2017, Glenn F. Matthews
# Copyright (c) 2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for the ISOInfo helper class."""

import logging

from distutils.version import StrictVersion
import mock

from COT.helpers.tests.test_helper import HelperTestCase
from COT.helpers.isoinfo import ISOInfo

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc,protected-access


class TestISOInfo(HelperTestCase):
    """Test cases for ISOInfo helper class.

    Currently isoinfo isn't installable in Travis CI so we mock it out.
    """

    def setUp(self):
        """Pre-test setup."""
        self.helper = ISOInfo()
        super(TestISOInfo, self).setUp()

    @mock.patch('COT.helpers.helper.check_output',
                return_value=("isoinfo 3.00 (--) Copyright (C) 1993-1999 "
                              "Eric Youngdale (C) 1999-2010 Jörg Schilling"))
    def test_get_version(self, _):
        """Test .version getter logic for genisoimage."""
        self.helper._installed = True
        self.assertEqual(StrictVersion("3.00"), self.helper.version)

    @mock.patch('COT.helpers.helper.check_output',
                return_value=("""
Setting input-charset to 'UTF-8' from locale.

Directory listing of /
d---------   0    0    0  2048 Dec 12 2012 [   23 02] .
d---------   0    0    0  2048 Dec 12 2012 [   23 02] ..
----------   0    0    0   175 Dec 12 2012 [   24 00] IOSXR_CONFIG.TXT;1
----------   0    0    0    64 Dec 11 2012 [   25 00] IOSXR_CONFIG_ADMIN.TXT;1
"""))
    def test_call_cache(self, mock_check_output):
        """ISO information is cached and replayed appropriately."""
        self.helper._installed = True
        args = ('-i', self.input_iso, '-l')
        output = self.helper.call(args)
        # Output should be stored in the cache
        self.assertEqual(output, self.helper.cached_output[args])
        mock_check_output.assert_called_once()

        mock_check_output.reset_mock()
        mock_check_output.return_value = "Gotcha!"
        # Cache should be used by default
        output2 = self.helper.call(args)
        self.assertEqual(output, output2)
        mock_check_output.assert_not_called()

        # Cache can be disregarded if desired
        output3 = self.helper.call(args, use_cached=False)
        self.assertEqual(output3, "Gotcha!")
        mock_check_output.assert_called_once()

    @mock.patch('COT.helpers.helper.check_output', return_value="")
    def test_call_noop_nocache(self, _):
        """Not all calls are cached."""
        # Call is a no-op but succeeds. Nothing to cache
        self.helper._installed = True
        self.helper.call(['-i', self.input_iso])
        self.assertDictEqual(self.helper.cached_output, {})
