#!/usr/bin/env python
#
# test_raw.py - Unit test cases for RAW disk representation.
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

"""Unit test cases for RAW subclass of DiskRepresentation."""

import logging
import os

from distutils.version import StrictVersion
import mock

from COT.tests import COTTestCase
from COT.disks import RAW, VMDK, DiskRepresentation
from COT.helpers import HelperError

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc


class TestRAW(COTTestCase):
    """Test cases for RAW disk image representation."""

    def test_representation_invalid(self):
        """Representation of a file that isn't really a raw disk."""
        fake_raw = RAW(self.input_iso)
        with self.assertRaises(HelperError):
            assert fake_raw.files

    def test_convert_from_vmdk(self):
        """Test conversion of a RAW image from a VMDK."""
        old = DiskRepresentation.from_file(self.blank_vmdk)
        raw = RAW.from_other_image(old, self.temp_dir)

        self.assertEqual(raw.disk_format, 'raw')
        self.assertEqual(raw.disk_subformat, None)

    @mock.patch('COT.helpers.qemu_img.QEMUImg.version',
                new_callable=mock.PropertyMock,
                return_value=StrictVersion("1.0.0"))
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('COT.helpers.qemu_img.QEMUImg.call')
    @mock.patch('COT.helpers.vmdktool.VMDKTool.call')
    def test_convert_from_vmdk_old_qemu(self, mock_vmdktool, mock_qemuimg, *_):
        """Test conversion from streamOptimized VMDK with old QEMU."""
        RAW.from_other_image(VMDK(self.blank_vmdk), self.temp_dir)

        mock_vmdktool.assert_called_with([
            '-s', os.path.join(self.temp_dir, "blank.img"), self.blank_vmdk])
        mock_qemuimg.assert_not_called()

    @mock.patch('COT.helpers.qemu_img.QEMUImg.version',
                new_callable=mock.PropertyMock,
                return_value=StrictVersion("1.2.0"))
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('COT.helpers.qemu_img.QEMUImg.call')
    @mock.patch('COT.helpers.vmdktool.VMDKTool.call')
    def test_convert_from_vmdk_new_qemu(self, mock_vmdktool, mock_qemuimg, *_):
        """Test conversion from streamOptimized VMDK with new QEMU."""
        RAW.from_other_image(VMDK(self.blank_vmdk), self.temp_dir)

        mock_vmdktool.assert_not_called()
        mock_qemuimg.assert_called_with([
            'convert', '-O', 'raw', self.blank_vmdk,
            os.path.join(self.temp_dir, "blank.img")])

    def test_create_with_capacity(self):
        """Creation of a raw image of a particular size."""
        disk_path = os.path.join(self.temp_dir, "out.raw")
        RAW.create_file(disk_path, capacity="16M")
        raw = RAW(disk_path)
        self.assertEqual(raw.disk_format, 'raw')
        self.assertEqual(raw.disk_subformat, None)

    def test_create_with_files(self):
        """Creation of a raw image with specific file contents."""
        disk_path = os.path.join(self.temp_dir, "out.raw")
        RAW.create_file(disk_path, files=[self.input_ovf])
        raw = RAW(disk_path)
        self.assertEqual(raw.files,
                         [os.path.basename(self.input_ovf)])
        self.assertEqual(raw.capacity, "8388608")

    def test_create_with_files_and_capacity(self):
        """Creation of raw image with specified capacity and file contents."""
        disk_path = os.path.join(self.temp_dir, "out.img")
        RAW.create_file(disk_path, files=[self.input_ovf], capacity="64M")
        raw = RAW(disk_path)
        self.assertEqual(raw.files,
                         [os.path.basename(self.input_ovf)])
        self.assertEqual(raw.capacity, "67108864")
