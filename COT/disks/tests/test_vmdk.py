#!/usr/bin/env python
#
# test_vmdk.py - Unit test cases for VMDK disk representation.
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

"""Unit test cases for VMDK subclass of DiskRepresentation."""

import logging
import os

from distutils.version import StrictVersion
import mock

from COT.tests import COTTestCase
from COT.disks import VMDK, DiskRepresentation
from COT.helpers import helpers, HelperError

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc

QEMU_VERSION_WARNING = {
    "levelname": 'WARNING',
    "msg": "QEMU version.*ESXi will reject",
}


class TestVMDK(COTTestCase):
    """Generic test cases for VMDK class."""

    def test_capacity(self):
        """Check capacity of several VMDK files."""
        vmdk1 = VMDK(path=self.blank_vmdk)
        self.assertEqual(vmdk1.capacity, "536870912")

        vmdk2 = VMDK(path=self.input_vmdk)
        self.assertEqual(vmdk2.capacity, "1073741824")

    def test_create_default(self):
        """Default creation logic."""
        disk_path = os.path.join(self.temp_dir, "foo.vmdk")
        VMDK.create_file(path=disk_path, capacity="16M")
        vmdk = VMDK(disk_path)
        self.assertEqual(vmdk.path, os.path.join(self.temp_dir, "foo.vmdk"))
        self.assertEqual(vmdk.disk_format, "vmdk")
        self.assertEqual(vmdk.disk_subformat, "streamOptimized")
        self.assertEqual(vmdk.disk_subformat, "streamOptimized")
        if helpers['qemu-img'].version < StrictVersion("2.5.1"):
            self.assertLogged(**QEMU_VERSION_WARNING)

    def test_create_stream_optimized(self):
        """Explicit subformat specification."""
        disk_path = os.path.join(self.temp_dir, "foo.vmdk")
        VMDK.create_file(path=disk_path, capacity="16M",
                         disk_subformat="streamOptimized")
        vmdk = VMDK(disk_path)
        self.assertEqual(vmdk.path, os.path.join(self.temp_dir, "foo.vmdk"))
        self.assertEqual(vmdk.disk_format, "vmdk")
        self.assertEqual(vmdk.disk_subformat, "streamOptimized")
        self.assertEqual(vmdk.disk_subformat, "streamOptimized")
        if helpers['qemu-img'].version < StrictVersion("2.5.1"):
            self.assertLogged(**QEMU_VERSION_WARNING)

    def test_create_monolithic_sparse(self):
        """Explicit subformat specification."""
        disk_path = os.path.join(self.temp_dir, "foo.vmdk")
        VMDK.create_file(path=disk_path, capacity="16M",
                         disk_subformat="monolithicSparse")
        vmdk = VMDK(disk_path)
        self.assertEqual(vmdk.path, os.path.join(self.temp_dir, "foo.vmdk"))
        self.assertEqual(vmdk.disk_format, "vmdk")
        self.assertEqual(vmdk.disk_subformat, "monolithicSparse")
        self.assertEqual(vmdk.disk_subformat, "monolithicSparse")

    def test_create_files_unsupported(self):
        """No support for creating a VMDK with a filesystem."""
        self.assertRaises(NotImplementedError,
                          VMDK.create_file,
                          path=os.path.join(self.temp_dir, "foo.vmdk"),
                          disk_subformat="monolithicSparse",
                          files=[self.input_iso])


class TestVMDKConversion(COTTestCase):
    """Test cases for VMDK.from_other_image method."""

    def setUp(self):
        """Pre-test setup."""
        super(TestVMDKConversion, self).setUp()
        self.input_image_paths = {}
        self.input_disks = {}
        for disk_format in ["raw", "qcow2", "vmdk"]:
            temp_disk = os.path.join(self.temp_dir,
                                     "foo.{0}".format(disk_format))
            helpers['qemu-img'].call(['create', '-f', disk_format,
                                      temp_disk, "16M"])
            self.input_disks[disk_format] = DiskRepresentation.from_file(
                temp_disk)

    def other_format_to_vmdk_test(self, disk_format,
                                  output_subformat="streamOptimized"):
        """Test conversion of various formats to vmdk."""
        vmdk = VMDK.from_other_image(self.input_disks[disk_format],
                                     self.temp_dir, output_subformat)

        self.assertEqual(vmdk.disk_format, 'vmdk')
        self.assertEqual(vmdk.disk_subformat, output_subformat)

    @mock.patch('COT.helpers.qemu_img.QEMUImg.version',
                new_callable=mock.PropertyMock,
                return_value=StrictVersion("1.2.0"))
    @mock.patch('COT.helpers.qemu_img.QEMUImg.call',
                wraps=helpers["qemu-img"].call)
    @mock.patch('COT.helpers.vmdktool.VMDKTool.call',
                wraps=helpers["vmdktool"].call)
    def test_disk_conversion_old_qemu(self,
                                      mock_vmdktool_call, mock_qemu_call, _):
        """Test disk conversion flows with old qemu-img version.

        This version doesn't support streamOptimized output at all,
        so we'll use vmdktool instead.
        """
        for disk_format in ["raw", "qcow2", "vmdk"]:
            self.other_format_to_vmdk_test(disk_format)

            for call_args in mock_qemu_call.call_args_list:
                self.assertNotIn('convert', call_args)
            mock_vmdktool_call.assert_called_once()

            mock_qemu_call.reset_mock()
            mock_vmdktool_call.reset_mock()

    @mock.patch('COT.helpers.qemu_img.QEMUImg.version',
                new_callable=mock.PropertyMock,
                return_value=StrictVersion("2.1.0"))
    @mock.patch('COT.helpers.qemu_img.QEMUImg.call',
                wraps=helpers["qemu-img"].call)
    @mock.patch('COT.helpers.vmdktool.VMDKTool.call',
                wraps=helpers["vmdktool"].call)
    def test_disk_conversion_med_qemu(self,
                                      mock_vmdktool_call, mock_qemu_call, _):
        """Test disk conversion flows with intermediate qemu-img version.

        This version produces streamOptimized VMDKs but they're version 1
        rather than version 3, which makes ESXi unhappy. Therefore,
        we still prefer vmdktool, but fall back to qemu-img with a warning
        if vmdktool is not available.
        """
        # First, with vmdktool, same as previous test case
        for disk_format in ["raw", "qcow2", "vmdk"]:
            self.other_format_to_vmdk_test(disk_format)

            for call_args in mock_qemu_call.call_args_list:
                self.assertNotIn('convert', call_args)
            mock_vmdktool_call.assert_called_once()

            mock_qemu_call.reset_mock()
            mock_vmdktool_call.reset_mock()

        # Now, disable vmdktool
        with mock.patch("COT.helpers.vmdktool.VMDKTool.installed",
                        new_callable=mock.PropertyMock, return_value=False),\
            mock.patch("COT.helpers.vmdktool.VMDKTool.installable",
                       new_callable=mock.PropertyMock, return_value=False):
            for disk_format in ["raw", "qcow2", "vmdk"]:
                self.other_format_to_vmdk_test(disk_format)

                # Since we lack vmdktool, and we have a technically
                # new enough version of qemu-img, we call it, under protest.
                mock_qemu_call.assert_called_once()
                self.assertLogged(**QEMU_VERSION_WARNING)
                mock_vmdktool_call.assert_not_called()

                mock_qemu_call.reset_mock()
                mock_vmdktool_call.reset_mock()

    @mock.patch('COT.helpers.qemu_img.QEMUImg.version',
                new_callable=mock.PropertyMock,
                return_value=StrictVersion("2.5.1"))
    @mock.patch('COT.helpers.qemu_img.QEMUImg.call',
                wraps=helpers["qemu-img"].call)
    @mock.patch('COT.helpers.vmdktool.VMDKTool.call',
                wraps=helpers["vmdktool"].call)
    def test_disk_conversion_new_qemu(self,
                                      mock_vmdktool_call, mock_qemu_call, _):
        """Test disk conversion flows with newer qemu-img version.

        This version produces version 3 streamOptimized VMDKs,
        so we don't need to use vmdktool.
        """
        for disk_format in ["raw", "qcow2", "vmdk"]:
            self.other_format_to_vmdk_test(disk_format)

            mock_qemu_call.assert_called_once()
            mock_vmdktool_call.assert_not_called()

            mock_qemu_call.reset_mock()

    def test_disk_conversion_unsupported_subformat(self):
        """qemu-img will fail if subformat is invalid."""
        self.assertRaises(HelperError,
                          self.other_format_to_vmdk_test,
                          'qcow2', output_subformat="foobar")
