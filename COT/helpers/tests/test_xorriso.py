#!/usr/bin/env python
#
# test_xorriso.py - Unit test cases for XorrISO class.
#
# October 2016, Glenn F. Matthews
# Copyright (c) 2014-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for the XorrISO class."""

import logging

from distutils.version import StrictVersion
import mock

from COT.helpers.tests.test_helper import HelperUT
from COT.helpers.mkisofs import XorrISO

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc,protected-access


class TestXorrISO(HelperUT):
    """Test cases for XorrISO helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = XorrISO()
        super(TestXorrISO, self).setUp()

    @mock.patch('COT.helpers.helper.check_output', return_value="""
xorriso 1.3.2 : RockRidge filesystem manipulator, libburnia project.

xorriso 1.3.2
ISO 9660 Rock Ridge filesystem manipulator and CD/DVD/BD burn program
Copyright (C) 2013, Thomas Schmitt <scdbackup@gmx.net>, libburnia project.
xorriso version   :  1.3.2
Version timestamp :  2013.08.07.110001
Build timestamp   :  -none-given-
libisofs   in use :  1.3.4  (min. 1.3.2)
libjte     in use :  1.0.0  (min. 1.0.0)
libburn    in use :  1.3.4  (min. 1.3.4)
libburn OS adapter:  internal GNU/Linux SG_IO adapter sg-linux
libisoburn in use :  1.3.2  (min. 1.3.2)
Provided under GNU GPL version 2 or later.
There is NO WARRANTY, to the extent permitted by law.
""")
    def test_get_version(self, _):
        """Test .version getter logic for xorriso."""
        self.helper._installed = True
        self.assertEqual(StrictVersion("1.3.2"), self.helper.version)

    @mock.patch('COT.helpers.helper.check_output')
    @mock.patch('subprocess.check_call')
    def test_install_already_present(self, mock_check_call, mock_check_output):
        """Don't re-install if already installed."""
        self.helper._installed = True
        self.helper.install()
        mock_check_output.assert_not_called()
        mock_check_call.assert_not_called()

    def test_install_helper_apt_get(self):
        """Test installation via 'apt-get' of xorriso."""
        self.apt_install_test('xorriso', 'xorriso')
