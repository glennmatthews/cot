#!/usr/bin/env python
# coding=utf-8
#
# test_mkisofs.py - Unit test cases for MkISOFS helper class.
#
# March 2015, Glenn F. Matthews
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

"""Unit test cases for the MkISOFS helper class."""

import logging

from distutils.version import StrictVersion
import mock

from COT.helpers.tests.test_helper import HelperUT
from COT.helpers.mkisofs import MkISOFS

# pylint: disable=missing-type-doc,missing-param-doc,protected-access

logger = logging.getLogger(__name__)


class TestMkISOFS(HelperUT):
    """Test cases for MkISOFS helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = MkISOFS()
        super(TestMkISOFS, self).setUp()

    @mock.patch('COT.helpers.helper.check_output',
                return_value=("mkisofs 3.00 (--) Copyright (C) 1993-1997 "
                              "Eric Youngdale (C) 1997-2010 Jörg Schilling"))
    def test_get_version_mkisofs(self, _):
        """Test .version getter logic for mkisofs."""
        self.helper._installed = True
        self.assertEqual(StrictVersion("3.0"), self.helper.version)

    @mock.patch('COT.helpers.helper.check_output')
    @mock.patch('subprocess.check_call')
    def test_install_helper_already_present(self, mock_check_call,
                                            mock_check_output):
        """Don't re-install if already installed."""
        self.helper._installed = True
        self.helper.install()
        mock_check_output.assert_not_called()
        mock_check_call.assert_not_called()

    def test_install_helper_brew(self):
        """Test installation via 'brew'."""
        self.brew_install_test('cdrtools')

    def test_install_helper_port(self):
        """Test installation via 'port'."""
        self.port_install_test('cdrtools')
