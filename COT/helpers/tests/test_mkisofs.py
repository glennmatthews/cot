#!/usr/bin/env python
# coding=utf-8
#
# test_mkisofs.py - Unit test cases for COT.helpers.mkisofs submodule.
#
# March 2015, Glenn F. Matthews
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

"""Unit test cases for the COT.helpers.mkisofs submodule."""

import subprocess

from distutils.version import StrictVersion
import mock

from COT.helpers.tests.test_helper import HelperUT
from COT.helpers.mkisofs import MkIsoFS


class TestMkIsoFS(HelperUT):
    """Test cases for MkIsoFS helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = MkIsoFS()
        super(TestMkIsoFS, self).setUp()

    @mock.patch('COT.helpers.helper.Helper._check_output',
                return_value=("mkisofs 3.00 (--) Copyright (C) 1993-1997 "
                              "Eric Youngdale (C) 1997-2010 Jörg Schilling"))
    def test_get_version_mkisofs(self, _):
        """Test .version getter logic for mkisofs."""
        self.assertEqual(StrictVersion("3.0"), self.helper.version)

    @mock.patch('COT.helpers.helper.Helper._check_output',
                return_value="genisoimage 1.1.11 (Linux)")
    def test_get_version_genisoimage(self, _):
        """Test .version getter logic for genisoimage."""
        self.assertEqual(StrictVersion("1.1.11"), self.helper.version)

    @mock.patch('COT.helpers.helper.Helper._check_output', return_value="""
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
    def test_get_version_xorriso(self, _):
        """Test .version getter logic for xorriso."""
        self.assertEqual(StrictVersion("1.3.2"), self.helper.version)

    @mock.patch('distutils.spawn.find_executable')
    @mock.patch("COT.helpers.mkisofs.MkIsoFS.call_helper")
    def test_find_mkisofs(self, mock_call_helper, mock_find_executable):
        """If mkisofs is found, use it."""
        def find_one(name):
            """Find mkisofs but no other."""
            if name == "mkisofs":
                return "/mkisofs"
            return None
        mock_find_executable.side_effect = find_one
        self.assertEqual("mkisofs", self.helper.name)
        self.assertEqual(self.helper.path, "/mkisofs")

        self.helper.create_iso('foo.iso', [self.input_ovf])
        mock_call_helper.assert_called_with(
            ['-output', 'foo.iso', '-full-iso9660-filenames',
             '-iso-level', '2', self.input_ovf])

    @mock.patch('distutils.spawn.find_executable')
    @mock.patch("COT.helpers.mkisofs.MkIsoFS.call_helper")
    def test_find_genisoimage(self, mock_call_helper, mock_find_executable):
        """If mkisofs is not found, but genisoimage is, use that."""
        def find_one(name):
            """Find genisoimage but no other."""
            if name == "genisoimage":
                return "/genisoimage"
            return None
        mock_find_executable.side_effect = find_one
        self.assertEqual("genisoimage", self.helper.name)
        self.assertEqual(self.helper.path, "/genisoimage")

        self.helper.create_iso('foo.iso', [self.input_ovf])
        mock_call_helper.assert_called_with(
            ['-output', 'foo.iso', '-full-iso9660-filenames',
             '-iso-level', '2', self.input_ovf])

    @mock.patch('distutils.spawn.find_executable')
    @mock.patch("COT.helpers.mkisofs.MkIsoFS.call_helper")
    def test_find_xorriso(self, mock_call_helper, mock_find_executable):
        """If mkisofs and genisoimage are not found, but xorriso is, use it."""
        def find_one(name):
            """Find xorriso but no other."""
            if name == "xorriso":
                return "/xorriso"
            return None
        mock_find_executable.side_effect = find_one
        self.assertEqual("xorriso", self.helper.name)
        self.assertEqual(self.helper.path, "/xorriso")

        self.helper.create_iso('foo.iso', [self.input_ovf])
        mock_call_helper.assert_called_with(
            ['-as', 'mkisofs', '-output', 'foo.iso', '-full-iso9660-filenames',
             '-iso-level', '2', self.input_ovf])

    @mock.patch('COT.helpers.helper.Helper._check_output')
    @mock.patch('subprocess.check_call')
    def test_install_helper_already_present(self, mock_check_call,
                                            mock_check_output):
        """Don't re-install if already installed."""
        self.helper.install_helper()
        mock_check_output.assert_not_called()
        mock_check_call.assert_not_called()
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_port(self):
        """Test installation via 'port'."""
        self.port_install_test('cdrtools')

    def test_install_helper_apt_get(self):
        """Test installation via 'apt-get' of genisoimage."""
        self.apt_install_test('genisoimage', 'genisoimage')

    @mock.patch('distutils.spawn.find_executable', return_value=None)
    @mock.patch('subprocess.check_call')
    @mock.patch(
        'COT.helpers.helper.Helper._check_output',
        return_value="is not installed and no information is available"
    )
    def test_install_helper_apt_get_xorriso(self,
                                            mock_check_output,
                                            mock_check_call,
                                            *_):
        """Test installation via 'apt-get' of xorriso."""
        self.enable_apt_install()
        mock_check_call.side_effect = [
            None,  # apt-get update
            subprocess.CalledProcessError(
                100, "Unable to locate package"),  # install genisoimage
            subprocess.CalledProcessError(
                100, "Unable to locate package"),  # sudo install genisoimage
            None,  # install xorriso
        ]

        self.helper.install_helper()
        self.assertSubprocessCalls(mock_check_output,
                                   [['dpkg', '-s', 'genisoimage'],
                                    ['dpkg', '-s', 'xorriso']])
        self.assertSubprocessCalls(
            mock_check_call,
            [['apt-get', '-q', 'update'],
             ['apt-get', '-q', 'install', 'genisoimage'],
             ['sudo', 'apt-get', '-q', 'install', 'genisoimage'],
             ['apt-get', '-q', 'install', 'xorriso']])
        self.assertEqual(self.helper.name, 'xorriso')
