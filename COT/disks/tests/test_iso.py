#!/usr/bin/env python
#
# test_iso.py - Unit test cases for ISO disk representation.
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

"""Unit test cases for ISO subclass of DiskRepresentation."""

import logging
import os
import mock

from COT.tests import COTTestCase
from COT.disks import ISO
from COT.helpers import (
    helpers, HelperError, HelperNotFoundError,
)

logger = logging.getLogger(__name__)

# pylint: disable=protected-access,missing-type-doc,missing-param-doc


class TestISO(COTTestCase):
    """Test cases for ISO class."""

    def setUp(self):
        """Test case setup function called automatically before each test."""
        super(TestISO, self).setUp()
        self.foo_iso = os.path.join(self.temp_dir, "foo.iso")

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        for name in ['mkisofs', 'genisoimage', 'xorriso', 'isoinfo']:
            helper = helpers[name]
            helper._installed = None
            helper._path = None
            helper._version = None
        super(TestISO, self).tearDown()

    def test_representation(self):
        """Representing an existing ISO."""
        iso = ISO(self.input_iso)
        self.assertEqual(iso.path, self.input_iso)
        self.assertEqual(iso.disk_format, 'iso')
        self.assertEqual(iso.capacity, str(self.FILE_SIZE['input.iso']))
        if helpers['isoinfo']:
            self.assertEqual(iso.disk_subformat, "")
            self.assertEqual(iso.files,
                             ['iosxr_config.txt', 'iosxr_config_admin.txt'])
        self.assertEqual(iso.predicted_drive_type, 'cdrom')

    def test_create_with_files(self):
        """Creation of a ISO with specific file contents."""
        disk_path = os.path.join(self.temp_dir, "out.iso")
        ISO.create_file(disk_path, files=[self.input_ovf])
        iso = ISO(disk_path)
        if helpers['isoinfo']:
            # Our default create format is rockridge
            self.assertEqual(iso.disk_subformat, "rockridge")
            self.assertEqual(iso.files,
                             [os.path.basename(self.input_ovf)])
        else:
            helpers['isoinfo']._installed = True

            with mock.patch.object(helpers['isoinfo'], "call",
                                   return_value="Rock Ridge extensions found"):
                self.assertEqual(iso.disk_subformat, "rockridge")

            with mock.patch.object(helpers['isoinfo'], "call",
                                   return_value="""
Setting input-charset to 'UTF-8' from locale.
/{0}
""".format(os.path.basename(self.input_ovf))):
                self.assertEqual(iso.files,
                                 [os.path.basename(self.input_ovf)])

    def test_create_with_files_non_rockridge(self):
        """Creation of a non-rock-ridge ISO with specific file contents."""
        disk_path = os.path.join(self.temp_dir, "out.iso")
        ISO.create_file(disk_path, files=[self.input_ovf], disk_subformat="")
        iso = ISO(disk_path)
        if helpers['isoinfo']:
            self.assertEqual(iso.disk_subformat, "")
            self.assertEqual(iso.files,
                             [os.path.basename(self.input_ovf)])
        else:
            helpers['isoinfo']._installed = True
            with mock.patch.object(helpers['isoinfo'], "call",
                                   return_value="No SUSP/Rock Ridge present"):
                self.assertEqual(iso.disk_subformat, "")

            with mock.patch.object(helpers['isoinfo'], "call",
                                   return_value="""
Setting input-charset to 'UTF-8' from locale.
/{0};1
""".format(os.path.basename(self.input_ovf).upper())):
                self.assertEqual(iso.files,
                                 [os.path.basename(self.input_ovf)])

    def test_create_without_files(self):
        """Can't create an empty ISO."""
        self.assertRaises(RuntimeError,
                          ISO.create_file,
                          path=os.path.join(self.temp_dir, "out.iso"),
                          capacity="100")

    @mock.patch("COT.helpers.mkisofs.MkISOFS.call")
    def test_create_with_mkisofs(self, mock_call):
        """Creation of an ISO with mkisofs (default)."""
        helpers['mkisofs']._installed = True
        ISO.create_file(path=self.foo_iso, files=[self.input_ovf])
        mock_call.assert_called_with(
            ['-output', self.foo_iso, '-full-iso9660-filenames',
             '-iso-level', '2', '-allow-lowercase', '-r', self.input_ovf])

    @mock.patch("COT.helpers.mkisofs.GenISOImage.call")
    def test_create_with_genisoimage(self, mock_call):
        """Creation of an ISO with genisoimage if mkisofs is unavailable."""
        helpers['mkisofs']._installed = False
        helpers['genisoimage']._installed = True
        ISO.create_file(path=self.foo_iso, files=[self.input_ovf])
        mock_call.assert_called_with(
            ['-output', self.foo_iso, '-full-iso9660-filenames',
             '-iso-level', '2', '-allow-lowercase', '-r', self.input_ovf])

    @mock.patch("COT.helpers.mkisofs.XorrISO.call")
    def test_create_with_xorriso(self, mock_call):
        """Creation of an ISO with xorriso as last resort."""
        helpers['mkisofs']._installed = False
        helpers['genisoimage']._installed = False
        helpers['xorriso']._installed = True
        ISO.create_file(path=self.foo_iso, files=[self.input_ovf])
        mock_call.assert_called_with(
            ['-as', 'mkisofs', '-output', self.foo_iso,
             '-full-iso9660-filenames', '-iso-level', '2', '-allow-lowercase',
             '-r', self.input_ovf])

    def test_create_no_helpers_available(self):
        """Creation of ISO should fail if no helpers are install[ed|able]."""
        helpers['mkisofs']._installed = False
        helpers['genisoimage']._installed = False
        helpers['xorriso']._installed = False
        helpers['apt-get']._installed = False
        helpers['brew']._installed = False
        helpers['port']._installed = False
        helpers['yum']._installed = False
        self.assertRaises(HelperNotFoundError,
                          ISO.create_file,
                          path=self.foo_iso,
                          files=[self.input_ovf])

    @mock.patch("COT.helpers.mkisofs.MkISOFS.call")
    def test_create_with_mkisofs_non_rockridge(self, mock_call):
        """Creation of a non-Rock-Ridge ISO with mkisofs (default)."""
        helpers['mkisofs']._installed = True
        ISO.create_file(path=self.foo_iso, files=[self.input_ovf],
                        disk_subformat="")
        mock_call.assert_called_with(
            ['-output', self.foo_iso, '-full-iso9660-filenames',
             '-iso-level', '2', '-allow-lowercase', self.input_ovf])

    def test_file_is_this_type_nonexistent(self):
        """Call file_is_this_type should fail if file doesn't exist."""
        self.assertRaises(HelperError,
                          ISO.file_is_this_type, "/foo/bar")

    def test_file_is_this_type_isoinfo(self):
        """The file_is_this_type API should use isoinfo if available."""
        if helpers['isoinfo']:
            self.assertTrue(ISO.file_is_this_type(self.input_iso))
            self.assertFalse(ISO.file_is_this_type(self.blank_vmdk))
        else:
            # Fake it til you make it
            helpers['isoinfo']._installed = True
            with mock.patch.object(helpers['isoinfo'], "call"):
                self.assertTrue(ISO.file_is_this_type(self.input_iso))
            with mock.patch.object(helpers['isoinfo'], "call",
                                   side_effect=HelperError):
                self.assertFalse(ISO.file_is_this_type(self.blank_vmdk))

    def test_file_is_this_type_noisoinfo(self):
        """The file_is_this_type API should work if isoinfo isn't available."""
        _isoinfo = helpers['isoinfo']
        helpers['isoinfo'] = False
        try:
            self.assertTrue(ISO.file_is_this_type(self.input_iso))
            self.assertFalse(ISO.file_is_this_type(self.blank_vmdk))
        finally:
            helpers['isoinfo'] = _isoinfo

    def test_from_other_image_unsupported(self):
        """No support for from_other_image."""
        self.assertRaises(NotImplementedError,
                          ISO.from_other_image,
                          self.blank_vmdk, self.temp_dir)
