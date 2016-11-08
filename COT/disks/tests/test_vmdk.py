#!/usr/bin/env python
#
# test_vmdk.py - Unit test cases for VMDK disk representation.
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

"""Unit test cases for VMDK subclass of DiskRepresentation."""

import logging
import os

from distutils.version import StrictVersion
import mock

from COT.tests.ut import COT_UT
from COT.disks import VMDK, disk_representation_from_file
from COT.helpers import helpers, HelperError

logger = logging.getLogger(__name__)

# pylint: disable=missing-type-doc,missing-param-doc


class TestVMDK(COT_UT):
    """Test cases for VMDK class."""

    def other_format_to_vmdk_test(self, disk_format,
                                  output_subformat="streamOptimized"):
        """Test conversion of various formats to vmdk."""
        temp_disk = os.path.join(self.temp_dir, "foo.{0}".format(disk_format))
        helpers['qemu-img'].call(['create', '-f', disk_format,
                                  temp_disk, "16M"])
        old = disk_representation_from_file(temp_disk)
        vmdk = VMDK.from_other_image(old, self.temp_dir, output_subformat)

        self.assertEqual(vmdk.disk_format, 'vmdk')
        self.assertEqual(vmdk.disk_subformat, output_subformat)

    @mock.patch('COT.helpers.qemu_img.QEMUImg.version',
                new_callable=mock.PropertyMock,
                return_value=StrictVersion("1.0.0"))
    def test_disk_conversion_old_qemu(self, _):
        """Test disk conversion flows with older qemu-img version."""
        self.other_format_to_vmdk_test('raw')
        self.other_format_to_vmdk_test('qcow2')
        self.other_format_to_vmdk_test('vmdk')

    @mock.patch('COT.helpers.qemu_img.QEMUImg.version',
                new_callable=mock.PropertyMock,
                return_value=StrictVersion("2.1.0"))
    def test_disk_conversion_new_qemu(self, _):
        """Test disk conversion flows with newer qemu-img version."""
        self.other_format_to_vmdk_test('raw')
        self.other_format_to_vmdk_test('qcow2')
        self.other_format_to_vmdk_test('vmdk')

    def test_disk_conversion_unsupported_subformat(self):
        """qemu-img will fail if subformat is invalid."""
        self.assertRaises(HelperError,
                          self.other_format_to_vmdk_test,
                          'qcow2', output_subformat="foobar")

    def test_capacity(self):
        """Check capacity of several VMDK files."""
        vmdk1 = VMDK(path=self.blank_vmdk)
        self.assertEqual(vmdk1.capacity, "536870912")

        vmdk2 = VMDK(path=self.input_vmdk)
        self.assertEqual(vmdk2.capacity, "1073741824")

    def test_create_default(self):
        """Default creation logic."""
        vmdk = VMDK(path=os.path.join(self.temp_dir, "foo.vmdk"),
                    capacity="16M")
        self.assertEqual(vmdk.path, os.path.join(self.temp_dir, "foo.vmdk"))
        self.assertEqual(vmdk.disk_format, "vmdk")
        self.assertEqual(vmdk.disk_subformat, "streamOptimized")
        self.assertEqual(vmdk.disk_subformat, "streamOptimized")

    def test_create_stream_optimized(self):
        """Explicit subformat specification."""
        vmdk = VMDK(path=os.path.join(self.temp_dir, "foo.vmdk"),
                    capacity="16M",
                    disk_subformat="streamOptimized")
        self.assertEqual(vmdk.path, os.path.join(self.temp_dir, "foo.vmdk"))
        self.assertEqual(vmdk.disk_format, "vmdk")
        self.assertEqual(vmdk.disk_subformat, "streamOptimized")
        self.assertEqual(vmdk.disk_subformat, "streamOptimized")

    def test_create_monolithic_sparse(self):
        """Explicit subformat specification."""
        vmdk = VMDK(path=os.path.join(self.temp_dir, "foo.vmdk"),
                    capacity="16M",
                    disk_subformat="monolithicSparse")
        self.assertEqual(vmdk.path, os.path.join(self.temp_dir, "foo.vmdk"))
        self.assertEqual(vmdk.disk_format, "vmdk")
        self.assertEqual(vmdk.disk_subformat, "monolithicSparse")
        self.assertEqual(vmdk.disk_subformat, "monolithicSparse")

    def test_create_files_unsupported(self):
        """No support for creating a VMDK with a filesystem."""
        self.assertRaises(NotImplementedError,
                          VMDK, path=os.path.join(self.temp_dir, "foo.vmdk"),
                          files=[self.input_iso])
