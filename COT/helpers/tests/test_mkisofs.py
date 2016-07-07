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

from distutils.version import StrictVersion

from COT.helpers.tests.test_helper import HelperUT
from COT.helpers.helper import Helper
from COT.helpers.mkisofs import MkIsoFS


class TestMkIsoFS(HelperUT):
    """Test cases for MkIsoFS helper class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.helper = MkIsoFS()
        super(TestMkIsoFS, self).setUp()

    def test_get_version_mkisofs(self):
        """Test .version getter logic for mkisofs."""
        self.fake_output = ("mkisofs 3.00 (--) Copyright (C) 1993-1997 "
                            "Eric Youngdale (C) 1997-2010 Jörg Schilling")
        self.assertEqual(StrictVersion("3.0"), self.helper.version)

    def test_get_version_genisoimage(self):
        """Test .version getter logic for genisoimage."""
        self.fake_output = "genisoimage 1.1.11 (Linux)"
        self.assertEqual(StrictVersion("1.1.11"), self.helper.version)

    def test_find_mkisofs(self):
        """If mkisofs is found, use it."""
        def find_one(_self, name):
            """Find mkisofs but no other."""
            if name == "mkisofs":
                return "/mkisofs"
            return None
        Helper.find_executable = find_one
        self.assertEqual("mkisofs", self.helper.name)
        self.assertEqual(self.helper.path, "/mkisofs")

    def test_find_genisoimage(self):
        """If mkisofs is not found, but genisoimage is, use that."""
        def find_one(_self, name):
            """Find genisoimage but no other."""
            if name == "genisoimage":
                return "/genisoimage"
            return None
        Helper.find_executable = find_one
        self.assertEqual("genisoimage", self.helper.name)
        self.assertEqual(self.helper.path, "/genisoimage")

    def test_install_helper_already_present(self):
        """Don't re-install if already installed."""
        self.helper.install_helper()
        self.assertEqual([], self.last_argv)
        self.assertLogged(**self.ALREADY_INSTALLED)

    def test_install_helper_port(self):
        """Test installation via 'port'."""
        self.port_install_test('cdrtools')

    def test_install_helper_apt_get(self):
        """Test installation via 'apt-get'."""
        self.apt_install_test('genisoimage')

    def test_install_helper_unsupported(self):
        """Installation fails with neither apt-get nor port nor yum."""
        self.select_package_manager(None)
        self.system = "Windows"
        with self.assertRaises(NotImplementedError):
            self.helper.install_helper()
