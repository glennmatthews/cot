#!/usr/bin/env python
#
# test_qemu_img.py - Unit test cases for COT.helpers.qemu_img submodule.
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

"""Unit test cases for the COT.helpers.qemu_img submodule."""

from distutils.version import StrictVersion
import mock

from COT.helpers.tests.test_helper import HelperUT
from COT.helpers.qemu_img import QEMUImg

# pylint: disable=missing-type-doc,missing-param-doc,protected-access


class TestQEMUImg(HelperUT):
    """Test cases for QEMUImg helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = QEMUImg()
        super(TestQEMUImg, self).setUp()

    @mock.patch('COT.helpers.helper.check_output')
    def test_older_version(self, mock_check_output):
        """Test .version getter logic for older versions."""
        mock_check_output.return_value = """
qemu-img version 1.4.2, Copyright (c) 2004-2008 Fabrice Bellard
usage: qemu-img command [command options]
QEMU disk image utility

Command syntax:
..."""
        self.helper._installed = True
        version = self.helper.version
        self.assertSubprocessCalls(mock_check_output,
                                   [['qemu-img', '--version']])
        self.assertEqual(version, StrictVersion("1.4.2"))

        # Output should be cached rather than re-invoking qemu-img
        mock_check_output.reset_mock()
        version = self.helper.version
        mock_check_output.assert_not_called()
        self.assertEqual(version, StrictVersion("1.4.2"))

    @mock.patch('COT.helpers.helper.check_output')
    def test_newer_version(self, mock_check_output):
        """Test .version getter logic for newer versions."""
        self.helper._installed = True
        mock_check_output.return_value = \
            "qemu-img version 2.1.2, Copyright (c) 2004-2008 Fabrice Bellard"
        self.assertEqual(self.helper.version,
                         StrictVersion("2.1.2"))

    @mock.patch('COT.helpers.helper.check_output')
    def test_invalid_version(self, mock_check_output):
        """Negative test for .version getter logic."""
        self.helper._installed = True
        mock_check_output.return_value = \
            "qemu-img: error: unknown argument --version"
        with self.assertRaises(RuntimeError):
            assert self.helper.version

    @mock.patch('subprocess.check_call')
    def test_install_already_present(self, mock_check_call):
        """Do nothing when trying to re-install."""
        self.helper._installed = True
        self.helper.install()
        mock_check_call.assert_not_called()

    def test_install_apt_get(self):
        """Test installation via 'apt-get'."""
        self.apt_install_test('qemu-utils', 'qemu-img')

    def test_install_brew(self):
        """Test installation via 'brew'."""
        self.brew_install_test('qemu')

    def test_install_port(self):
        """Test installation via 'port'."""
        self.port_install_test('qemu')

    def test_install_yum(self):
        """Test installation via 'yum'."""
        self.yum_install_test('qemu-img')
