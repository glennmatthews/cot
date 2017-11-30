#!/usr/bin/env python
#
# test_qcow2.py - Unit test cases for QCOW2 disk representation.
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

"""Unit test cases for QCOW2 subclass of DiskRepresentation."""

import logging
import os

from distutils.version import StrictVersion
import mock

from COT.tests import COTTestCase
from COT.disks import QCOW2, VMDK, RAW
from COT.helpers import helpers

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc


class TestQCOW2(COTTestCase):
    """Test cases for QCOW2 class."""

    def setUp(self):
        """Pre-testcase setup."""
        super(TestQCOW2, self).setUp()
        self.temp_disk = os.path.join(self.temp_dir, "blank.img")
        helpers['qemu-img'].call(['create', '-f', 'raw', self.temp_disk, "8M"])

    def test_init_with_files_unsupported(self):
        """Creation of a QCOW2 with specific file contents is not supported."""
        self.assertRaises(NotImplementedError,
                          QCOW2.create_file,
                          path=os.path.join(self.temp_dir, "out.qcow2"),
                          files=[self.input_ovf])

    def test_from_other_image_raw(self):
        """Test conversion of raw format to qcow2."""
        qcow2 = QCOW2.from_other_image(RAW(self.temp_disk), self.temp_dir)

        self.assertEqual(qcow2.disk_format, 'qcow2')
        self.assertEqual(qcow2.disk_subformat, None)
        self.assertEqual(qcow2.predicted_drive_type, 'harddisk')

    def test_from_other_image_vmdk(self):
        """Test conversion of streamOptimized vmdk format to qcow2."""
        qcow2 = QCOW2.from_other_image(VMDK(self.blank_vmdk), self.temp_dir)

        self.assertEqual(qcow2.disk_format, 'qcow2')
        self.assertEqual(qcow2.disk_subformat, None)
        self.assertEqual(qcow2.predicted_drive_type, 'harddisk')

    @mock.patch('COT.helpers.qemu_img.QEMUImg.version',
                new_callable=mock.PropertyMock,
                return_value=StrictVersion("1.0.0"))
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('COT.disks.raw.RAW.from_other_image')
    @mock.patch('COT.helpers.qemu_img.QEMUImg.call')
    def test_convert_from_vmdk_old_qemu(self,
                                        mock_qemuimg,
                                        mock_raw,
                                        *_):
        """Test conversion from streamOptimized VMDK with old QEMU."""
        mock_raw.return_value = RAW(self.temp_disk)

        QCOW2.from_other_image(VMDK(self.blank_vmdk), self.temp_dir)

        mock_qemuimg.assert_called_with([
            'convert', '-O', 'qcow2', self.temp_disk,
            os.path.join(self.temp_dir, 'blank.qcow2')
        ])

    @mock.patch('COT.helpers.qemu_img.QEMUImg.version',
                new_callable=mock.PropertyMock,
                return_value=StrictVersion("1.2.0"))
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('COT.helpers.qemu_img.QEMUImg.call')
    @mock.patch('COT.helpers.vmdktool.VMDKTool.call')
    def test_convert_from_vmdk_new_qemu(self, mock_vmdktool, mock_qemuimg, *_):
        """Test conversion from streamOptimized VMDK with new QEMU."""
        QCOW2.from_other_image(VMDK(self.blank_vmdk), self.temp_dir)

        mock_vmdktool.assert_not_called()
        mock_qemuimg.assert_called_with([
            'convert', '-O', 'qcow2', self.blank_vmdk,
            os.path.join(self.temp_dir, "blank.qcow2")])
