#!/usr/bin/env python
#
# test_genisoimage.py - Unit test cases for GenISOImage class.
#
# October 2016, Glenn F. Matthews
# Copyright (c) 2014-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for the GenISOImage class."""

import logging

from distutils.version import StrictVersion
import mock

from COT.helpers.tests.test_helper import HelperTestCase
from COT.helpers.mkisofs import GenISOImage

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc,protected-access


class TestGenISOImage(HelperTestCase):
    """Test cases for GenISOImage helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = GenISOImage()
        super(TestGenISOImage, self).setUp()

    @mock.patch('COT.helpers.helper.check_output',
                return_value="genisoimage 1.1.11 (Linux)")
    def test_get_version(self, _):
        """Test .version getter logic for genisoimage."""
        self.helper._installed = True
        self.assertEqual(StrictVersion("1.1.11"), self.helper.version)

    @mock.patch('COT.helpers.helper.check_output')
    @mock.patch('subprocess.check_call')
    def test_install_already_present(self, mock_check_call, mock_check_output):
        """Don't re-install if already installed."""
        self.helper._installed = True
        self.helper.install()
        mock_check_output.assert_not_called()
        mock_check_call.assert_not_called()

    def test_install_helper_apt_get(self):
        """Test installation via 'apt-get' of genisoimage."""
        self.apt_install_test('genisoimage', 'genisoimage')
