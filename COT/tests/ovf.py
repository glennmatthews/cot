#!/usr/bin/env python
#
# ovf.py - Unit test cases for COT OVF/OVA handling
#
# September 2013, Glenn F. Matthews
# Copyright (c) 2013-2014 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

import filecmp
import os.path
import tempfile
import shutil
import subprocess
import xml.etree.ElementTree as ET
import re
import tarfile
import unittest

from COT.tests.ut import COT_UT
from COT.ovf import OVF, OVFNameHelper, OVFItem
from COT.ovf import byte_count, byte_string, factor_bytes
from COT.vm_description import VMInitError
from COT.data_validation import ValueUnsupportedError
from COT.helper_tools import *

class TestByteString(unittest.TestCase):
    """Test cases for byte-count to string conversion functions"""

    def test_byte_count(self):
        self.assertEqual(byte_count("128", "byte"), 128)
        self.assertEqual(byte_count("1", "byte * 2^10"), 1024)

    def test_factor_bytes(self):
        self.assertEqual(factor_bytes("2147483648"), ("2", "byte * 2^30"))
        self.assertEqual(factor_bytes(2147483649), ("2147483649", "byte"))

    def test_byte_string(self):
        self.assertEqual(byte_string(1024), "1.00 kB")
        self.assertEqual(byte_string(250691584), "239.08 MB")
        self.assertEqual(byte_string(2560, base_shift=2), "2.50 GB")
        self.assertEqual(byte_string(512, base_shift=2), "512 MB")


class TestOVFInputOutput(COT_UT):
    """Test cases for OVF file input/output"""

    def setUp(self):
        super(TestOVFInputOutput, self).setUp()
        self.working_dir = tempfile.mkdtemp(prefix="cot_ut_ovfio")
        # Additional temp directory used by some test cases
        self.staging_dir = None


    def tearDown(self):
        shutil.rmtree(self.working_dir)
        if self.staging_dir:
            shutil.rmtree(self.staging_dir)
        super(TestOVFInputOutput, self).tearDown()


    def test_filename_validation(self):
        """Test class method(s) for filename validation.
        """
        self.assertEqual('.ovf', OVF.detect_type_from_name("/foo/bar/foo.ovf"))
        self.assertEqual('.ova', OVF.detect_type_from_name("/foo/bar/foo.ova"))
        # Lazy filenames should be OK too
        self.assertEqual('.ovf',
                         OVF.detect_type_from_name("/foo/bar/foo.ovf.5.2.2"))
        self.assertEqual('.ova',
                         OVF.detect_type_from_name("/foo/bar/foo.ova.15.4.T"))
        # Unsupported formats
        self.assertRaises(ValueUnsupportedError, OVF.detect_type_from_name,
                          "/foo/bar.ovf/baz")
        self.assertRaises(ValueUnsupportedError, OVF.detect_type_from_name,
                          "/foo/bar.zip")


    def test_input_output(self):
        """Read an OVF then write it again, verify no changes"""
        ovf = OVF(self.input_ovf, self.working_dir, self.temp_file)
        ovf.write()
        self.check_diff('')

        # Filename output too
        ovf = OVF(self.input_ovf, self.working_dir, self.temp_file + ".a.b.c")
        ovf.write()
        self.check_diff('', file2=(self.temp_file + ".a.b.c"))


    def test_input_output_v09(self):
        """Test reading/writing of a v0.9 OVF.
        """
        ovf = OVF(self.v09_ovf, self.working_dir, self.temp_file)
        ovf.write()
        self.check_diff('', file1=self.v09_ovf)


    def test_input_output_custom(self):
        """Test reading/writing of an OVF with custom extensions.
        """
        ovf = OVF(self.vmware_ovf, self.working_dir, self.temp_file)
        ovf.write()
        # VMware disagrees with COT on some fiddly details of the XML formatting
        self.check_diff(
"""
-<?xml version="1.0" encoding="UTF-8"?>
-<ovf:Envelope vmw:buildId="build-880146" xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:cim="http://schemas.dmtf.org/wbem/wscim/1/common" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vmw="http://www.vmware.com/schema/ovf" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
+<?xml version='1.0' encoding='utf-8'?>
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vmw="http://www.vmware.com/schema/ovf" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" vmw:buildId="build-880146">
   <ovf:References>
...
   </ovf:VirtualSystem>
-</ovf:Envelope>        
+</ovf:Envelope>""", file1=self.vmware_ovf)


    def test_input_output_missing_file(self):
        """Test reading/writing of an OVF with missing file references.
        """
        self.staging_dir = tempfile.mkdtemp(prefix="cot_ut_ovfio_stage")
        input_dir = os.path.dirname(self.input_ovf)
        shutil.copy(os.path.join(input_dir, 'input.ovf'), self.staging_dir)
        shutil.copy(os.path.join(input_dir, 'input.vmdk'), self.staging_dir)
        # Don't copy input.iso to the staging directory.
        ovf = OVF(os.path.join(self.staging_dir, 'input.ovf'),
                  self.working_dir,
                  os.path.join(self.temp_dir, "temp.ova"))

        self.assertFalse(ovf.validate_file_references(),
                         "OVF references missing file - contents are invalid")

        # Write out to OVA then read the OVA in as well.
        ovf.write()

        ova = OVF(os.path.join(self.temp_dir, "temp.ova"),
                  self.working_dir,
                  os.path.join(self.temp_dir, "temp.ovf"))
        self.assertFalse(ova.validate_file_references(),
                         "OVA references missing file - contents are invalid")
        ova.write()


    def test_input_output_bad_file(self):
        """Test reading/writing of an OVF with incorrect file references.
        """
        self.staging_dir = tempfile.mkdtemp(prefix="cot_ut_ovfio_stage")
        input_dir = os.path.dirname(self.input_ovf)
        shutil.copy(os.path.join(input_dir, 'input.ovf'), self.staging_dir)
        shutil.copy(os.path.join(input_dir, 'input.vmdk'), self.staging_dir)
        # Copy input.vmdk to input.iso so as to have the wrong size/checksum
        shutil.copy(os.path.join(input_dir, 'input.vmdk'),
                    os.path.join(self.staging_dir, 'input.iso'))
        # Don't copy input.iso to the staging directory.
        ovf = OVF(os.path.join(self.staging_dir, 'input.ovf'),
                  self.working_dir,
                  os.path.join(self.temp_dir, "temp.ova"))

        self.assertFalse(ovf.validate_file_references(),
                         "OVF has wrong file size - contents are invalid")

        # Write out to OVA (which will correct the file size information)
        ovf.write()

        # Now read in the OVA
        ova = OVF(os.path.join(self.temp_dir, "temp.ova"),
                  self.working_dir,
                  os.path.join(self.temp_dir, "temp.ovf"))
        # Replace the extracted fake .iso with the real .iso
        shutil.copy(os.path.join(input_dir, 'input.iso'), self.working_dir)
        self.assertFalse(ova.validate_file_references(),
                         "OVA has wrong file size - contents are invalid")

        # Write out to OVF
        ova.write()


    def test_tar_untar(self):
        """Output OVF to OVA and vice versa"""
        # Read OVF and write to OVA
        ovf = OVF(self.input_ovf, self.working_dir,
                  os.path.join(self.temp_dir, "temp.ova"))
        ovf.write()
        ovf = None
        # Read OVA and write to OVF
        ovf2 = OVF(os.path.join(self.temp_dir, "temp.ova"), self.working_dir,
                   os.path.join(self.temp_dir, "input.ovf"))
        ovf2.write()

        # Make sure everything propagated over successfully
        input_dir = os.path.dirname(self.input_ovf)
        for ext in ['.ovf', '.mf', '.iso', '.vmdk']:
            self.assertTrue(filecmp.cmp(
                    os.path.join(input_dir, "input" + ext),
                    os.path.join(self.temp_dir, "input" + ext)),
                            "{0} file changed after OVF->OVA->OVF conversion"
                            .format(ext))


    def test_invalid_ovf_file(self):
        """Check that various invalid input OVF files result in VMInitError
        rather than other miscellaneous exceptions.
        """
        fake_file = os.path.join(self.temp_dir, "foo.ovf")
        # .ovf that is an empty file
        with open(fake_file, 'w+') as f:
            f.write("")
        self.assertRaises(VMInitError, OVF, fake_file, self.working_dir, None)

        # .ovf that isn't actually XML at all
        with open(fake_file, 'w+') as f:
            f.write("< hello world!")
        self.assertRaises(VMInitError, OVF, fake_file, self.working_dir, None)

        # .ovf that is XML but not OVF XML
        with open(fake_file, 'w+') as f:
            f.write("<?xml version='1.0' encoding='utf-8'?>")
        self.assertRaises(VMInitError, OVF, fake_file, self.working_dir, None)
        with open(fake_file, 'w+') as f:
            f.write("<?xml version='1.0' encoding='utf-8'?>")
            f.write("<foo/>")
        self.assertRaises(VMInitError, OVF, fake_file, self.working_dir, None)


    def test_invalid_ova_file(self):
        """Check that various invalid input OVA files result in VMInitError
        rather than other miscellaneous exceptions.
        """
        fake_file = os.path.join(self.temp_dir, "foo.ova")
        # .ova that is an empty file
        with open(fake_file, 'w+') as f:
            f.write("")
        self.assertRaises(VMInitError, OVF, fake_file, self.working_dir, None)

        # .ova that is not a TAR file
        with open(fake_file, 'w+') as f:
            f.write("< hello world!")
        self.assertRaises(VMInitError, OVF, fake_file, self.working_dir, None)

        # .ova that is a TAR file but does not contain an OVF descriptor
        tarf = tarfile.open(fake_file, 'w')
        try:
            disk_path = os.path.join(os.path.dirname(__file__), "blank.vmdk")
            tarf.add(disk_path, os.path.basename(disk_path))
        finally:
            tarf.close()
        self.assertRaises(VMInitError, OVF, fake_file, self.working_dir, None)

        # .ova that contains an OVF descriptor but in the wrong position
        tarf = tarfile.open(fake_file, 'a')
        try:
            tarf.add(self.input_ovf, os.path.basename(self.input_ovf))
        finally:
            tarf.close()
        self.assertRaises(VMInitError, OVF, fake_file, self.working_dir, None)


    def test_invalid_ovf_contents(self):
        """Check for rejection of OVF files with valid XML but invalid data"""

        # Multiple Items under same profile with same InstanceID
        fake_file = os.path.join(self.temp_dir, "foo.ovf")
        with open(fake_file, "w") as f:
            subprocess.check_call(['sed', 's/InstanceID>11</InstanceID>10</',
                                   self.input_ovf],
                                  stdout=f)
        if COT_UT.OVFTOOL_PRESENT:
            # Make sure ovftool also sees this as invalid
            self.assertRaises(HelperError, validate_ovf_for_esxi, fake_file)
        self.assertRaises(VMInitError, OVF, fake_file, self.working_dir, None)

        # Item referencing a nonexistent Configuration
        with open(fake_file, "w") as f:
            subprocess.check_call(['sed', 's/on="2CPU-2GB-1NIC"/on="foo"/',
                                   self.input_ovf],
                                  stdout=f)
        if COT_UT.OVFTOOL_PRESENT:
            # Make sure ovftool also sees this as invalid
            self.assertRaises(HelperError, validate_ovf_for_esxi, fake_file)
        self.assertRaises(VMInitError, OVF, fake_file, self.working_dir, None)

        # TODO - inconsistent order of File versus Disk?
        # TODO - Sections in wrong order?

    def test_configuration_profiles(self):
        """Check profile id list APIs"""

        # No profiles defined
        ovf = OVF(self.vmware_ovf, self.working_dir, None)

        self.assertEqual(ovf.get_configuration_profile_ids(), [])

        self.assertEqual(ovf.get_default_profile_name(), None)

        # Profile list exists
        ovf = OVF(self.input_ovf, self.working_dir, None)

        # default profile is first in the list
        self.assertEqual(ovf.get_configuration_profile_ids(),
                         ["4CPU-4GB-3NIC",
                          "1CPU-1GB-1NIC",
                          "2CPU-2GB-1NIC"])

        self.assertEqual(ovf.get_default_profile_name(), "4CPU-4GB-3NIC")


class TestOVFItem(COT_UT):
    """Unit test cases for the OVFItem class"""

    def setUp(self):
        super(TestOVFItem, self).setUp()
        self.working_dir = tempfile.mkdtemp(prefix="cot_ut_ovfiitem")


    def tearDown(self):
        shutil.rmtree(self.working_dir)
        super(TestOVFItem, self).tearDown()

    def test_1_to_1(self):
        """Convert one Item to an OVFItem and back"""
        root = ET.fromstring(
"""<?xml version='1.0' encoding='utf-8'?>
<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vmw="http://www.vmware.com/schema/ovf" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData">
  <ovf:VirtualSystem ovf:id="test">
    <ovf:VirtualHardwareSection ovf:transport="iso">
      <ovf:Item>
        <rasd:Address>0</rasd:Address>
        <rasd:Description>SCSI Controller</rasd:Description>
        <rasd:ElementName>SCSI Controller 0</rasd:ElementName>
        <rasd:InstanceID>3</rasd:InstanceID>
        <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
        <rasd:ResourceType>6</rasd:ResourceType>
      </ovf:Item>
    </ovf:VirtualHardwareSection>
  </ovf:VirtualSystem>
</ovf:Envelope>""")
        helper = OVFNameHelper(1.0)
        input_item = (root.find(helper.VIRTUAL_SYSTEM)
                      .find(helper.VIRTUAL_HW_SECTION)
                      .find(helper.ITEM))

        ovfitem = OVFItem(None, input_item)
        item_list = ovfitem.generate_items()
        self.assertEqual(len(item_list), 1,
                         "Item list {0} should contain one Item"
                         .format(item_list))
        output_item = item_list[0]

        self.assertEqual(output_item.get(helper.ITEM_CONFIG),
                         input_item.get(helper.ITEM_CONFIG))
        for child in list(input_item):
            self.assertEqual(child.text,
                             output_item.find(child.tag).text)


    def test_remove_profile(self):
        """Test case for remove_profile() method
        """
        ovf = OVF(self.input_ovf, self.working_dir, self.temp_file)
        hw = ovf.hardware
        # InstanceID 11, NIC 0 (default, under all profiles)
        item = hw.item_dict['11']
        self.assertTrue(item.has_profile(None))
        self.assertTrue(item.has_profile("1CPU-1GB-1NIC"))
        self.assertTrue(item.has_profile("2CPU-2GB-1NIC"))
        self.assertTrue(item.has_profile("4CPU-4GB-3NIC"))
        # nonexistent profile
        self.assertFalse(item.has_profile("nonexistent"))

        # Remove one profile
        item.remove_profile("1CPU-1GB-1NIC")
        self.assertTrue(item.has_profile("4CPU-4GB-3NIC"))
        self.assertTrue(item.has_profile("2CPU-2GB-1NIC"))
        # no longer available
        self.assertFalse(item.has_profile(None))
        self.assertFalse(item.has_profile("1CPU-1GB-1NIC"))
        self.assertFalse(item.has_profile("nonexistent"))

        self.assertEqual(item.get_value(ovf.ADDRESS_ON_PARENT,
                                        ["2CPU-2GB-1NIC", "4CPU-4GB-3NIC"]),
                         "11")
        self.assertEqual(item.get_value(ovf.ADDRESS_ON_PARENT,
                                        ["1CPU-1GB-1NIC"]),
                         None)
        self.assertEqual(item.get_value(ovf.ADDRESS_ON_PARENT, [None]),
                         None)
        self.assertEqual(item.get_value(ovf.ADDRESS_ON_PARENT,
                                        ["1CPU-1GB-1NIC", "2CPU-2GB-1NIC",
                                         "4CPU-4GB-3NIC"]),
                         None)

        ovf.write()
        self.check_diff("""
       </ovf:Item>
-      <ovf:Item>
+      <ovf:Item ovf:configuration="2CPU-2GB-1NIC 4CPU-4GB-3NIC">
         <rasd:AddressOnParent>11</rasd:AddressOnParent>
""")


    def test_set_property(self):
        """Test cases for set_property() and related methods
        """
        ovf = OVF(self.input_ovf, self.working_dir, self.temp_file)
        hw = ovf.hardware
        # InstanceID 1, 'CPU' - entries for 'default' plus two other profiles
        item = hw.item_dict['1']

        self.assertTrue(item.has_profile(None))
        self.assertTrue(item.has_profile("2CPU-2GB-1NIC"))
        self.assertTrue(item.has_profile("4CPU-4GB-3NIC"))
        # implied by default profile
        self.assertTrue(item.has_profile("1CPU-1GB-1NIC"))
        # nonexistent profile
        self.assertFalse(item.has_profile("nonexistent"))

        self.assertEqual(item.get_value(ovf.VIRTUAL_QUANTITY,
                                        ['1CPU-1GB-1NIC']),
                         '1')
        self.assertEqual(item.get_value(ovf.VIRTUAL_QUANTITY,
                                        ['2CPU-2GB-1NIC']),
                         '2')
        # value differs between profiles, so get_value returns None
        self.assertEqual(item.get_value(ovf.VIRTUAL_QUANTITY,
                                        ['1CPU-1GB-1NIC', '2CPU-2GB-1NIC']),
                         None)

        # Set profile 1 to same as default (this is a no-op)
        item.set_property(ovf.VIRTUAL_QUANTITY, '1', ["1CPU-1GB-1NIC"])
        ovf.write()
        self.check_diff("")

        # Change profile 1 to same as profile 2
        item.set_property(ovf.VIRTUAL_QUANTITY, '2', ["1CPU-1GB-1NIC"])
        self.assertEqual(item.get_value(ovf.VIRTUAL_QUANTITY,
                                        ['1CPU-1GB-1NIC', '2CPU-2GB-1NIC']),
                         '2')
        ovf.write()
        self.check_diff("""
       </ovf:Item>
-      <ovf:Item ovf:configuration="2CPU-2GB-1NIC">
+      <ovf:Item ovf:configuration="1CPU-1GB-1NIC 2CPU-2GB-1NIC">
         <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
""")

        # Change profile 1 back under default
        item.set_property(ovf.VIRTUAL_QUANTITY, '1', ["1CPU-1GB-1NIC"])
        ovf.write()
        self.check_diff("")

        # Change profile 2 to fall under default
        item.set_property(ovf.VIRTUAL_QUANTITY, '1', ["2CPU-2GB-1NIC"])
        self.assertTrue(item.has_profile(None))
        self.assertTrue(item.has_profile("4CPU-4GB-3NIC"))
        # implied by default profile
        self.assertTrue(item.has_profile("1CPU-1GB-1NIC"))
        self.assertTrue(item.has_profile("2CPU-2GB-1NIC"))
        # nonexistent profile
        self.assertFalse(item.has_profile("nonexistent"))

        self.assertEqual(item.get_value(ovf.VIRTUAL_QUANTITY,
                                        ['1CPU-1GB-1NIC',
                                         '2CPU-2GB-1NIC']),
                         '1')
        self.assertEqual(item.get_value(ovf.VIRTUAL_QUANTITY, [None]),
                         '1')
        self.assertEqual(item.get_value(ovf.VIRTUAL_QUANTITY,
                                        [None, '1CPU-1GB-1NIC',
                                         '2CPU-2GB-1NIC']),
                         '1')
        # disjoint sets
        self.assertEqual(item.get_value(ovf.VIRTUAL_QUANTITY,
                                        [None, '1CPU-1GB-1NIC',
                                         '2CPU-2GB-1NIC', '4CPU-4GB-3NIC']),
                         None)

        ovf.write()
        self.check_diff("""
       </ovf:Item>
-      <ovf:Item ovf:configuration="2CPU-2GB-1NIC">
-        <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
-        <rasd:Description>Number of Virtual CPUs</rasd:Description>
-        <rasd:ElementName>2 virtual CPU(s)</rasd:ElementName>
-        <rasd:InstanceID>1</rasd:InstanceID>
-        <rasd:ResourceType>3</rasd:ResourceType>
-        <rasd:VirtualQuantity>2</rasd:VirtualQuantity>
-        <vmw:CoresPerSocket ovf:required="false">1</vmw:CoresPerSocket>
-      </ovf:Item>
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
""")



class TestOVFAddDisk(COT_UT):
    """Test cases for "cot add-disk" command with OVF files"""

    def setUp(self):
        """Test case setup function called automatically before each test"""
        self.new_vmdk = os.path.join(os.path.dirname(__file__), "blank.vmdk")
        super(TestOVFAddDisk, self).setUp()


    def call_add_disk(self, argv, result=0, input=None):
        """Call "cot add-disk" with typical arguments"""
        if input is None:
            input = self.input_ovf
        new_argv = ['add-disk', self.new_vmdk, input,
                    '-o', self.temp_file] + argv
        return self.call_cot(new_argv, result)


    def test_new_hard_disk(self):
        """Adding a new hard disk to the OVF"""

        # With default arguments
        self.call_add_disk([])
        # Default controller for generic platform is IDE for hard disks
        self.check_diff(
"""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="blank.vmdk" ovf:id="blank.vmdk" ovf:size="{blank_size}" />
   </ovf:References>
...
     <ovf:Disk ovf:capacity="1" ovf:capacityAllocationUnits="byte * 2^30" ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
+    <ovf:Disk ovf:capacity="512" ovf:capacityAllocationUnits="byte * 2^20" ovf:diskId="blank.vmdk" ovf:fileRef="blank.vmdk" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
   </ovf:DiskSection>
...
       </ovf:Item>
+      <ovf:Item>
+        <rasd:AddressOnParent>0</rasd:AddressOnParent>
+        <rasd:ElementName>Hard Disk Drive</rasd:ElementName>
+        <rasd:HostResource>ovf:/disk/blank.vmdk</rasd:HostResource>
+        <rasd:InstanceID>14</rasd:InstanceID>
+        <rasd:Parent>5</rasd:Parent>
+        <rasd:ResourceType>17</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           blank_size=self.FILE_SIZE['blank.vmdk']))
        # Make sure the disk file is copied over
        self.assertTrue(filecmp.cmp(self.new_vmdk,
                                    os.path.join(self.temp_dir, "blank.vmdk")),
                        "disk file should be exported unchanged")

        # Create new controller with specified address
        self.call_add_disk(['-c', 'scsi', '-a', '1:0'])
        self.check_diff(
"""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="blank.vmdk" ovf:id="blank.vmdk" ovf:size="{blank_size}" />
   </ovf:References>
...
     <ovf:Disk ovf:capacity="1" ovf:capacityAllocationUnits="byte * 2^30" ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
+    <ovf:Disk ovf:capacity="512" ovf:capacityAllocationUnits="byte * 2^20" ovf:diskId="blank.vmdk" ovf:fileRef="blank.vmdk" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
   </ovf:DiskSection>
...
       </ovf:Item>
+      <ovf:Item>
+        <rasd:Address>1</rasd:Address>
+        <rasd:Description>SCSI Controller 1</rasd:Description>
+        <rasd:ElementName>SCSI Controller</rasd:ElementName>
+        <rasd:InstanceID>14</rasd:InstanceID>
+        <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
+        <rasd:ResourceType>6</rasd:ResourceType>
+      </ovf:Item>
+      <ovf:Item>
+        <rasd:AddressOnParent>0</rasd:AddressOnParent>
+        <rasd:ElementName>Hard Disk Drive</rasd:ElementName>
+        <rasd:HostResource>ovf:/disk/blank.vmdk</rasd:HostResource>
+        <rasd:InstanceID>15</rasd:InstanceID>
+        <rasd:Parent>14</rasd:Parent>
+        <rasd:ResourceType>17</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           blank_size=self.FILE_SIZE['blank.vmdk']))
        # Make sure the disk file is copied over
        self.assertTrue(filecmp.cmp(self.new_vmdk,
                                    os.path.join(self.temp_dir, "blank.vmdk")),
                        "disk file should be exported unchanged")

        # Since the primary IDE0 controller is already full in the IOSv OVF,
        # COT will need to automatically create IDE1 controller
        self.call_add_disk([], input=self.iosv_ovf)
        self.check_diff(file1=self.iosv_ovf,
expected="""
     <ovf:File ovf:href="input.vmdk" ovf:id="vios-adventerprisek9-m.vmdk" ovf:size="{input_size}" />
+    <ovf:File ovf:href="blank.vmdk" ovf:id="blank.vmdk" ovf:size="{blank_size}" />
   </ovf:References>
...
     <ovf:Disk ovf:capacity="1073741824" ovf:capacityAllocationUnits="byte" ovf:diskId="vios-adventerprisek9-m.vmdk" ovf:fileRef="vios-adventerprisek9-m.vmdk" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
+    <ovf:Disk ovf:capacity="512" ovf:capacityAllocationUnits="byte * 2^20" ovf:diskId="blank.vmdk" ovf:fileRef="blank.vmdk" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
   </ovf:DiskSection>
...
       </ovf:Item>
+      <ovf:Item>
+        <rasd:Address>1</rasd:Address>
+        <rasd:Description>IDE Controller 1</rasd:Description>
+        <rasd:ElementName>IDE Controller</rasd:ElementName>
+        <rasd:InstanceID>6</rasd:InstanceID>
+        <rasd:ResourceSubType>virtio</rasd:ResourceSubType>
+        <rasd:ResourceType>5</rasd:ResourceType>
+      </ovf:Item>
+      <ovf:Item>
+        <rasd:AddressOnParent>0</rasd:AddressOnParent>
+        <rasd:ElementName>Hard Disk Drive</rasd:ElementName>
+        <rasd:HostResource>ovf:/disk/blank.vmdk</rasd:HostResource>
+        <rasd:InstanceID>7</rasd:InstanceID>
+        <rasd:Parent>6</rasd:Parent>
+        <rasd:ResourceType>17</rasd:ResourceType>
+      </ovf:Item>
       <ovf:Item ovf:required="false">
""".format(input_size=self.FILE_SIZE['input.vmdk'],
           blank_size=self.FILE_SIZE['blank.vmdk']))

    def test_new_hard_disk_v09(self):
        """Add a new hard disk to a v0.9 OVF.
        """
        self.call_add_disk([], input=self.v09_ovf)
        # Default controller for generic platform is IDE for hard disks
        self.check_diff(file1=self.v09_ovf,
expected="""
     <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{input_size}" />
+    <ovf:File ovf:href="blank.vmdk" ovf:id="blank.vmdk" ovf:size="{blank_size}" />
   </ovf:References>
...
     <ovf:Disk ovf:capacity="1073741824" ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/specifications/vmdk.html#sparse" />
+    <ovf:Disk ovf:capacity="536870912" ovf:diskId="blank.vmdk" ovf:fileRef="blank.vmdk" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
   </ovf:Section>
...
       </ovf:Item>
+      <ovf:Item>
+        <rasd:Caption>Hard Disk Drive</rasd:Caption>
+        <rasd:InstanceId>9</rasd:InstanceId>
+        <rasd:ResourceType>17</rasd:ResourceType>
+        <rasd:HostResource>/disk/blank.vmdk</rasd:HostResource>
+        <rasd:Parent>5</rasd:Parent>
+        <rasd:AddressOnParent>1</rasd:AddressOnParent>
+      </ovf:Item>
     </ovf:Section>
""".format(input_size=self.FILE_SIZE['input.vmdk'],
           blank_size=self.FILE_SIZE['blank.vmdk']))


    def test_overwrite_hard_disk(self):
        """Overwrite an existing hard disk with a new one"""
        # Overwrite by specifying file-id
        self.call_add_disk(['-f', 'file1'])
        self.check_diff(
"""
   <ovf:References>
-    <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{input_size}" />
+    <ovf:File ovf:href="blank.vmdk" ovf:id="file1" ovf:size="{blank_size}" />
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
...
     <ovf:Info>Virtual disk information</ovf:Info>
-    <ovf:Disk ovf:capacity="1" ovf:capacityAllocationUnits="byte * 2^30" ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
+    <ovf:Disk ovf:capacity="512" ovf:capacityAllocationUnits="byte * 2^20" ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
   </ovf:DiskSection>
""".format(input_size=self.FILE_SIZE['input.vmdk'],
           blank_size=self.FILE_SIZE['blank.vmdk'],
           iso_size=self.FILE_SIZE['input.iso']))
        # Make sure the old disk is not copied
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir,
                                                     "input.vmdk")),
                         "old disk should be replaced, not exported")
        # Make sure the new disk is copied
        self.assertTrue(filecmp.cmp(self.new_vmdk,
                                    os.path.join(self.temp_dir, "blank.vmdk")),
                        "newly added disk should be exported unchanged")

        # Overwrite by specifying controller address
        self.call_add_disk(['-c', 'scsi', '-a', '0:0'])
        self.check_diff(
"""
   <ovf:References>
-    <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{input_size}" />
+    <ovf:File ovf:href="blank.vmdk" ovf:id="file1" ovf:size="{blank_size}" />
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
...
     <ovf:Info>Virtual disk information</ovf:Info>
-    <ovf:Disk ovf:capacity="1" ovf:capacityAllocationUnits="byte * 2^30" ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
+    <ovf:Disk ovf:capacity="512" ovf:capacityAllocationUnits="byte * 2^20" ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
   </ovf:DiskSection>
""".format(input_size=self.FILE_SIZE['input.vmdk'],
           blank_size=self.FILE_SIZE['blank.vmdk'],
           iso_size=self.FILE_SIZE['input.iso']))
        # Make sure the old disk is not copied
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir,
                                                     "input.vmdk")),
                         "old disk should be replaced, not exported")
        # Make sure the new disk is copied
        self.assertTrue(filecmp.cmp(self.new_vmdk,
                                    os.path.join(self.temp_dir, "blank.vmdk")),
                        "new disk should be exported unchanged")


    def test_conflicting_args(self):
        """Test conflicting arguments are detected and rejected"""
        # file2 exists and is mapped to IDE 1:0 but we request IDE 1:1
        self.call_add_disk(['-c', 'ide', '-a', '1:1', '-f', 'file2'], result=1)


    def test_disk_conversion(self):
        """Make sure that disks are properly converted to stream-optimized
        VMDK format before embedding.
        """
        # Create a qcow2 image and add it as a new disk
        new_qcow2 = os.path.join(self.temp_dir, "new.qcow2")
        # Make it a small file to keep the test fast
        create_disk_image(new_qcow2, capacity="16M")
        new_argv = ['add-disk', new_qcow2, self.input_ovf,
                    '-c', 'scsi', '-o', self.temp_file]
        self.call_cot(new_argv, 0)

        # Make sure the disk was converted and added to the OVF
        self.check_diff(
"""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="new.vmdk" ovf:id="new.vmdk" ovf:size="{new_size}" />
   </ovf:References>
...
     <ovf:Disk ovf:capacity="1" ovf:capacityAllocationUnits="byte * 2^30" ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
+    <ovf:Disk ovf:capacity="16" ovf:capacityAllocationUnits="byte * 2^20" ovf:diskId="new.vmdk" ovf:fileRef="new.vmdk" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
   </ovf:DiskSection>
...
       </ovf:Item>
+      <ovf:Item>
+        <rasd:AddressOnParent>1</rasd:AddressOnParent>
+        <rasd:ElementName>Hard Disk Drive</rasd:ElementName>
+        <rasd:HostResource>ovf:/disk/new.vmdk</rasd:HostResource>
+        <rasd:InstanceID>14</rasd:InstanceID>
+        <rasd:Parent>3</rasd:Parent>
+        <rasd:ResourceType>17</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           new_size=os.path.getsize(os.path.join(self.temp_dir, "new.vmdk"))))
        # Make sure the disk was actually converted to the right format
        format, subformat = get_disk_format(os.path.join(self.temp_dir,
                                                         "new.vmdk"))
        self.assertEqual(format, 'vmdk')
        self.assertEqual(subformat, "streamOptimized")


    def test_disk_conversion_and_replacement(self):
        """Convert a disk to implicitly replace an existing disk"""
        # Create a qcow2 image and add it as a replacement for the existing vmdk
        new_qcow2 = os.path.join(self.temp_dir, "input.qcow2")
        # Keep it small!
        create_disk_image(new_qcow2, capacity="16M")
        new_argv = ['add-disk', new_qcow2, self.input_ovf,
                    '-o', self.temp_file]
        self.call_cot(new_argv, 0)

        # Make sure the disk was converted and replaced the existing disk
        self.check_diff(
"""
   <ovf:References>
-    <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{input_size}" />
+    <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{new_size}" />
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
...
     <ovf:Info>Virtual disk information</ovf:Info>
-    <ovf:Disk ovf:capacity="1" ovf:capacityAllocationUnits="byte * 2^30" ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
+    <ovf:Disk ovf:capacity="16" ovf:capacityAllocationUnits="byte * 2^20" ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
   </ovf:DiskSection>
""".format(input_size=self.FILE_SIZE['input.vmdk'],
           iso_size=self.FILE_SIZE['input.iso'],
           new_size=os.path.getsize(os.path.join(self.temp_dir, "input.vmdk"))))


    def test_add_disk_no_existing(self):
        """Add a disk to an OVF that doesn't currently have any.
        Verify correct creation of various OVF sub-sections."""
        self.call_cot(['add-disk', self.new_vmdk, self.minimal_ovf,
                       '-o', self.temp_file])
        self.check_diff(file1=self.minimal_ovf,
expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
-  <ovf:References />
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">
+  <ovf:References>
+    <ovf:File ovf:href="blank.vmdk" ovf:id="blank.vmdk" ovf:size="{blank_size}" />
+  </ovf:References>
+  <ovf:DiskSection>
+    <ovf:Info>Virtual disk information</ovf:Info>
+    <ovf:Disk ovf:capacity="512" ovf:capacityAllocationUnits="byte * 2^20" ovf:diskId="blank.vmdk" ovf:fileRef="blank.vmdk" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
+  </ovf:DiskSection>
   <ovf:VirtualSystem ovf:id="x">
...
       <ovf:Info />
+      <ovf:Item>
+        <rasd:Address>0</rasd:Address>
+        <rasd:Description>IDE Controller 0</rasd:Description>
+        <rasd:ElementName>IDE Controller</rasd:ElementName>
+        <rasd:InstanceID>1</rasd:InstanceID>
+        <rasd:ResourceType>5</rasd:ResourceType>
+      </ovf:Item>
+      <ovf:Item>
+        <rasd:AddressOnParent>0</rasd:AddressOnParent>
+        <rasd:ElementName>Hard Disk Drive</rasd:ElementName>
+        <rasd:HostResource>ovf:/disk/blank.vmdk</rasd:HostResource>
+        <rasd:InstanceID>2</rasd:InstanceID>
+        <rasd:Parent>1</rasd:Parent>
+        <rasd:ResourceType>17</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""".format(blank_size=self.FILE_SIZE['blank.vmdk']))


class TestOVFAddFile(COT_UT):
    """Test cases for "cot add-file" command with OVF files.
    Since add-file is a subset of add-disk, there aren't many of these.
    """

    def test_add_file(self):
        self.call_cot(['add-file', self.iosv_ovf, self.input_ovf,
                      '-o', self.temp_file])
        self.check_diff("""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="iosv.ovf" ovf:id="iosv.ovf" ovf:size="{ovf_size}" />
   </ovf:References>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           ovf_size=os.path.getsize(self.iosv_ovf)))

    def test_add_file_with_id(self):
        """Call 'cot add-file' with explicit '--file-id' argument.
        """
        self.call_cot(['add-file', self.iosv_ovf, self.input_ovf,
                       '-o', self.temp_file, '--file-id', 'myfile'])
        self.check_diff("""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="iosv.ovf" ovf:id="myfile" ovf:size="{ovf_size}" />
   </ovf:References>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           ovf_size=os.path.getsize(self.iosv_ovf)))


class TestOVFEditHardware(COT_UT):
    """Test cases for "cot edit-hardware" command with OVF files"""

    def test_no_work(self):
        """Call 'cot edit-hardware' with no work to do"""
        self.call_cot(['edit-hardware', self.input_ovf], result=2)


    def call_edit_hardware(self, argv, result=0, input=None):
        """Call 'cot edit-hardware' with typical arguments"""
        if input is None:
            input = self.input_ovf
        new_argv = ['edit-hardware', input,
                    '-o', self.temp_file] + argv
        return self.call_cot(new_argv, result)


    def test_set_system_type(self):
        """Set the VirtualSystemType"""
        for cli_opt in ['-v', '--virtual-system-type']:
            # Single type
            self.call_edit_hardware([cli_opt, 'vmx-09'])

            self.check_diff(
"""
         <vssd:VirtualSystemIdentifier>test</vssd:VirtualSystemIdentifier>
-        <vssd:VirtualSystemType>vmx-07 vmx-08</vssd:VirtualSystemType>
+        <vssd:VirtualSystemType>vmx-09</vssd:VirtualSystemType>
       </ovf:System>
""")

            # Multiple types
            self.call_edit_hardware([cli_opt, 'vmx-07', 'vmx-08', 'vmx-09',
                                     'Cisco:Internal:VMCloud-01'])
            self.check_diff(
"""
         <vssd:VirtualSystemIdentifier>test</vssd:VirtualSystemIdentifier>
-        <vssd:VirtualSystemType>vmx-07 vmx-08</vssd:VirtualSystemType>
+        <vssd:VirtualSystemType>vmx-07 vmx-08 vmx-09 Cisco:Internal:VMCloud-01</vssd:VirtualSystemType>
       </ovf:System>
""")


    def test_set_system_type_no_existing(self):
        """Add a VirtualSystemType to an OVF that doesn't have any.
        """
        self.call_edit_hardware(['--virtual-system-type', 'vmx-07', 'vmx-08'],
                                input=self.minimal_ovf)
        self.check_diff(file1=self.minimal_ovf,
expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData">
   <ovf:References />
...
       <ovf:Info />
+      <ovf:System>
+        <vssd:ElementName>Virtual System Type</vssd:ElementName>
+        <vssd:InstanceID>0</vssd:InstanceID>
+        <vssd:VirtualSystemType>vmx-07 vmx-08</vssd:VirtualSystemType>
+      </ovf:System>
     </ovf:VirtualHardwareSection>
""")


    def test_set_cpus(self):
        """Set the number of CPUs"""
        for cli_opt in ['-c', '--cpus']:
            # Change value under a specific profile:
            self.call_edit_hardware([cli_opt, '8', '-p', '2CPU-2GB-1NIC'])
            self.check_diff(
"""
         <rasd:Description>Number of Virtual CPUs</rasd:Description>
-        <rasd:ElementName>2 virtual CPU(s)</rasd:ElementName>
+        <rasd:ElementName>8 virtual CPU(s)</rasd:ElementName>
         <rasd:InstanceID>1</rasd:InstanceID>
         <rasd:ResourceType>3</rasd:ResourceType>
-        <rasd:VirtualQuantity>2</rasd:VirtualQuantity>
+        <rasd:VirtualQuantity>8</rasd:VirtualQuantity>
         <vmw:CoresPerSocket ovf:required="false">1</vmw:CoresPerSocket>
""")
            # Change value under a specific profile to match another profile:
            self.call_edit_hardware([cli_opt, '4', '-p', '2CPU-2GB-1NIC'])
            self.check_diff(
"""
       </ovf:Item>
-      <ovf:Item ovf:configuration="2CPU-2GB-1NIC">
-        <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
-        <rasd:Description>Number of Virtual CPUs</rasd:Description>
-        <rasd:ElementName>2 virtual CPU(s)</rasd:ElementName>
-        <rasd:InstanceID>1</rasd:InstanceID>
-        <rasd:ResourceType>3</rasd:ResourceType>
-        <rasd:VirtualQuantity>2</rasd:VirtualQuantity>
-        <vmw:CoresPerSocket ovf:required="false">1</vmw:CoresPerSocket>
-      </ovf:Item>
-      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+      <ovf:Item ovf:configuration="2CPU-2GB-1NIC 4CPU-4GB-3NIC">
         <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
""")
            # Change value under all profiles.
            # This results in merging the separate Items together
            # into a single shared Item:
            self.call_edit_hardware([cli_opt, '1'])
            self.check_diff(
"""
      </ovf:Item>
-      <ovf:Item ovf:configuration="2CPU-2GB-1NIC">
-        <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
-        <rasd:Description>Number of Virtual CPUs</rasd:Description>
-        <rasd:ElementName>2 virtual CPU(s)</rasd:ElementName>
-        <rasd:InstanceID>1</rasd:InstanceID>
-        <rasd:ResourceType>3</rasd:ResourceType>
-        <rasd:VirtualQuantity>2</rasd:VirtualQuantity>
-        <vmw:CoresPerSocket ovf:required="false">1</vmw:CoresPerSocket>
-      </ovf:Item>
-      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
-        <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
-        <rasd:Description>Number of Virtual CPUs</rasd:Description>
-        <rasd:ElementName>4 virtual CPU(s)</rasd:ElementName>
-        <rasd:InstanceID>1</rasd:InstanceID>
-        <rasd:ResourceType>3</rasd:ResourceType>
-        <rasd:VirtualQuantity>4</rasd:VirtualQuantity>
-        <vmw:CoresPerSocket ovf:required="false">1</vmw:CoresPerSocket>
-      </ovf:Item>
       <ovf:Item>
""")


    def test_set_cpus_no_existing(self):
        """Create a CPU definition in an OVF that doesn't have one"""
        self.call_edit_hardware(['--cpus', '1'], input=self.minimal_ovf)
        self.check_diff(file1=self.minimal_ovf,
expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">
   <ovf:References />
...
       <ovf:Info />
+      <ovf:Item>
+        <rasd:ElementName>cpu</rasd:ElementName>
+        <rasd:InstanceID>1</rasd:InstanceID>
+        <rasd:ResourceType>3</rasd:ResourceType>
+        <rasd:VirtualQuantity>1</rasd:VirtualQuantity>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")


    def test_set_memory(self):
        """Set the amount of RAM"""
        for cli_opt in ['-m', '--memory']:
            # Change value under a specific profile:
            self.call_edit_hardware([cli_opt, '3072', '-p', '2CPU-2GB-1NIC'])
            self.check_diff(
"""
         <rasd:Description>Memory Size</rasd:Description>
-        <rasd:ElementName>2048MB of memory</rasd:ElementName>
+        <rasd:ElementName>3072MB of memory</rasd:ElementName>
         <rasd:InstanceID>2</rasd:InstanceID>
         <rasd:ResourceType>4</rasd:ResourceType>
-        <rasd:VirtualQuantity>2048</rasd:VirtualQuantity>
+        <rasd:VirtualQuantity>3072</rasd:VirtualQuantity>
       </ovf:Item>
""")
            # Change value under all profiles.
            # This results in merging multiple Items into one.
            self.call_edit_hardware([cli_opt, '3072'])
            self.check_diff(
"""
         <rasd:Description>Memory Size</rasd:Description>
-        <rasd:ElementName>1024MB of memory</rasd:ElementName>
+        <rasd:ElementName>3072MB of memory</rasd:ElementName>
         <rasd:InstanceID>2</rasd:InstanceID>
         <rasd:ResourceType>4</rasd:ResourceType>
-        <rasd:VirtualQuantity>1024</rasd:VirtualQuantity>
-      </ovf:Item>
-      <ovf:Item ovf:configuration="2CPU-2GB-1NIC">
-        <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
-        <rasd:Description>Memory Size</rasd:Description>
-        <rasd:ElementName>2048MB of memory</rasd:ElementName>
-        <rasd:InstanceID>2</rasd:InstanceID>
-        <rasd:ResourceType>4</rasd:ResourceType>
-        <rasd:VirtualQuantity>2048</rasd:VirtualQuantity>
-      </ovf:Item>
-      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
-        <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
-        <rasd:Description>Memory Size</rasd:Description>
-        <rasd:ElementName>4096MB of memory</rasd:ElementName>
-        <rasd:InstanceID>2</rasd:InstanceID>
-        <rasd:ResourceType>4</rasd:ResourceType>
-        <rasd:VirtualQuantity>4096</rasd:VirtualQuantity>
+        <rasd:VirtualQuantity>3072</rasd:VirtualQuantity>
       </ovf:Item>
""")


    def test_set_memory_no_existing(self):
        """Create a RAM definition in an OVF that doesn't have one"""
        self.call_edit_hardware(['--memory', '4GB'], input=self.minimal_ovf)
        self.check_diff(file1=self.minimal_ovf,
expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">
   <ovf:References />
...
       <ovf:Info />
+      <ovf:Item>
+        <rasd:ElementName>memory</rasd:ElementName>
+        <rasd:InstanceID>1</rasd:InstanceID>
+        <rasd:ResourceType>4</rasd:ResourceType>
+        <rasd:VirtualQuantity>4096</rasd:VirtualQuantity>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")


    def test_set_nic_type(self):
        """Set the NIC hardware type"""
        for cli_opt in ['--nic-type']:
            for type in ['e1000', 'virtio']:
                TYPE = type.upper()
                # Change type under a specific profile:
                self.call_edit_hardware([cli_opt, type, '-p', '4CPU-4GB-3NIC'])
                # This requires cloning the "default" NIC under instance 11
                # to create a profile-specific version of this NIC
                self.check_diff(
"""
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:AddressOnParent>11</rasd:AddressOnParent>
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Description>""" + TYPE + """ ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:InstanceID>11</rasd:InstanceID>
+        <rasd:ResourceSubType>""" + TYPE + """</rasd:ResourceSubType>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
+      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
         <rasd:AddressOnParent>12</rasd:AddressOnParent>
...
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:Description>""" + TYPE + """ ethernet adapter on "VM Network"</rasd:Description>
         <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>""" + TYPE + """</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
...
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:Description>""" + TYPE + """ ethernet adapter on "VM Network"</rasd:Description>
         <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>""" + TYPE + """</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
""")
                # Change type under all profiles:
                self.call_edit_hardware([cli_opt, type])
                self.check_diff(
"""
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:Description>""" + TYPE + """ ethernet adapter on "VM Network"</rasd:Description>
         <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>""" + TYPE + """</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
...
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:Description>""" + TYPE + """ ethernet adapter on "VM Network"</rasd:Description>
         <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>""" + TYPE + """</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
...
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:Description>""" + TYPE + """ ethernet adapter on "VM Network"</rasd:Description>
         <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>""" + TYPE + """</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
""")


    def test_set_nic_type_no_existing(self):
        """Set NIC subtype for an OVF with no NICs (no-op)."""
        self.call_edit_hardware(['--nic-type', 'virtio'],
                                input=self.minimal_ovf)
        self.check_diff("", file1=self.minimal_ovf)


    def test_set_nic_count(self):
        """Test addition and removal of NICs"""

        # Add NICs from the "large" profile to the "small" profile as well
        self.call_edit_hardware(['--nics', '3', '--profile', '2CPU-2GB-1NIC'])
        self.check_diff(
"""
       </ovf:Item>
-      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+      <ovf:Item ovf:configuration="2CPU-2GB-1NIC 4CPU-4GB-3NIC">
         <rasd:AddressOnParent>12</rasd:AddressOnParent>
...
       </ovf:Item>
-      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+      <ovf:Item ovf:configuration="2CPU-2GB-1NIC 4CPU-4GB-3NIC">
         <rasd:AddressOnParent>13</rasd:AddressOnParent>
""")

        # Create a new NIC under the "large" profile
        self.call_edit_hardware(['--nics', '4', '--profile', '4CPU-4GB-3NIC'])
        self.check_diff(
"""
       </ovf:Item>
+      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:AddressOnParent>14</rasd:AddressOnParent>
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:ElementName>Ethernet4</rasd:ElementName>
+        <rasd:InstanceID>14</rasd:InstanceID>
+        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")


    def test_set_nic_network(self):
        """Test creation of networks and mapping of NICs to networks"""
        # Create a new network and map to it under one profile
        # This involves splitting the existing NIC into two items
        self.call_edit_hardware(['--nic-networks', 'UT', '-p', '2CPU-2GB-1NIC'])
        self.check_diff(
"""
       <ovf:Description>VM Network</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="UT">
+      <ovf:Description>UT</ovf:Description>
     </ovf:Network>
...
       </ovf:Item>
+      <ovf:Item ovf:configuration="2CPU-2GB-1NIC">
+        <rasd:AddressOnParent>11</rasd:AddressOnParent>
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Connection>UT</rasd:Connection>
+        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:InstanceID>11</rasd:InstanceID>
+        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
""")

        # Change the mapping across all profiles
        self.call_edit_hardware(['-N', 'UT', 'UT', 'UT'])
        self.check_diff(
"""
       <ovf:Description>VM Network</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="UT">
+      <ovf:Description>UT</ovf:Description>
     </ovf:Network>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
""")

        # Specify fewer networks than NICs to test implicit NIC assignment
        # (remaining NICs get the last network in the list)
        self.call_edit_hardware(['-N', 'UT1', 'UT2'])
        self.check_diff(
"""
       <ovf:Description>VM Network</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="UT1">
+      <ovf:Description>UT1</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="UT2">
+      <ovf:Description>UT2</ovf:Description>
     </ovf:Network>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT1</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT2</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT2</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
""")

    def test_set_nic_mac_address(self):
        """Test setting NIC MAC addresses"""

        # Set the same MAC address on all NICs on all profiles
        self.call_edit_hardware(['-M', '10:20:30:40:50:60'])
        self.check_diff(
"""
       <ovf:Item>
+        <rasd:Address>10:20:30:40:50:60</rasd:Address>
         <rasd:AddressOnParent>11</rasd:AddressOnParent>
...
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>10:20:30:40:50:60</rasd:Address>
         <rasd:AddressOnParent>12</rasd:AddressOnParent>
...
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>10:20:30:40:50:60</rasd:Address>
         <rasd:AddressOnParent>13</rasd:AddressOnParent>
""")

        # Set a sequence of MAC addresses under all profiles
        self.call_edit_hardware(['--mac-addresses', '10:20:30:40:50:60',
                                 '01:02:03:04:05:06', 'ab:cd:ef:00:00:00'])
        self.check_diff(
"""
       <ovf:Item>
+        <rasd:Address>10:20:30:40:50:60</rasd:Address>
         <rasd:AddressOnParent>11</rasd:AddressOnParent>
...
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>01:02:03:04:05:06</rasd:Address>
         <rasd:AddressOnParent>12</rasd:AddressOnParent>
...
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>ab:cd:ef:00:00:00</rasd:Address>
         <rasd:AddressOnParent>13</rasd:AddressOnParent>
""")


    def test_set_nic_name(self):
        """Test changing NIC name strings"""

        # Explicitly name each NIC
        self.call_edit_hardware(['--nic-names', 'foo', 'bar', 'baz'])
        self.check_diff(
"""
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:ElementName>foo</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:ElementName>bar</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:ElementName>baz</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
""")

        # More names than NICs
        self.call_edit_hardware(['--nic-names', 'foo', 'bar', 'baz', 'bat'])
        self.check_diff(
"""
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:ElementName>foo</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:ElementName>bar</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:ElementName>baz</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
""")

        # Fewer names than NICs
        self.call_edit_hardware(['--nic-names', 'foo', 'bar'])
        self.check_diff(
"""
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:ElementName>foo</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:ElementName>bar</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:ElementName>bar</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
""")

        # Pattern only
        self.call_edit_hardware(['--nic-names', 'eth{0}'])
        self.check_diff(
"""
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:ElementName>eth0</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:ElementName>eth1</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:ElementName>eth2</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
""")

        # Name + pattern
        self.call_edit_hardware(['--nic-names', 'foo', 'eth{10}'])
        self.check_diff(
"""
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:ElementName>foo</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:ElementName>eth10</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:ElementName>eth11</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
""")


    def test_set_nic_kitchen_sink(self):
        """Test changing many NIC properties at once"""

        # Change type, network mapping, and MACs simultaneously
        self.call_edit_hardware(['--nic-type', 'e1000',
                                 '--nic-networks', 'UT1', 'UT2', 'UT3',
                                 '--mac-addresses', '00:00:00:00:00:01',
                                 '11:22:33:44:55:66', 'fe:fd:fc:fb:fa:f9'])
        self.check_diff(
"""
       <ovf:Description>VM Network</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="UT1">
+      <ovf:Description>UT1</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="UT2">
+      <ovf:Description>UT2</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="UT3">
+      <ovf:Description>UT3</ovf:Description>
     </ovf:Network>
...
       <ovf:Item>
+        <rasd:Address>00:00:00:00:00:01</rasd:Address>
         <rasd:AddressOnParent>11</rasd:AddressOnParent>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:Connection>UT1</rasd:Connection>
+        <rasd:Description>E1000 ethernet adapter on "VM Network"</rasd:Description>
         <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>E1000</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
...
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>11:22:33:44:55:66</rasd:Address>
         <rasd:AddressOnParent>12</rasd:AddressOnParent>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:Connection>UT2</rasd:Connection>
+        <rasd:Description>E1000 ethernet adapter on "VM Network"</rasd:Description>
         <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>E1000</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
...
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>fe:fd:fc:fb:fa:f9</rasd:Address>
         <rasd:AddressOnParent>13</rasd:AddressOnParent>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:Connection>UT3</rasd:Connection>
+        <rasd:Description>E1000 ethernet adapter on "VM Network"</rasd:Description>
         <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>E1000</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
""")

        # Create a NIC and set networks under a single profile
        self.call_edit_hardware(['-n', '4', '-p', '4CPU-4GB-3NIC',
                                 '-N', 'UT'])
        self.check_diff(
"""
       <ovf:Description>VM Network</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="UT">
+      <ovf:Description>UT</ovf:Description>
     </ovf:Network>
...
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:AddressOnParent>11</rasd:AddressOnParent>
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Connection>UT</rasd:Connection>
+        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:InstanceID>11</rasd:InstanceID>
+        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
+      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
         <rasd:AddressOnParent>12</rasd:AddressOnParent>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
...
         <rasd:InstanceID>13</rasd:InstanceID>
+        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
+      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:AddressOnParent>14</rasd:AddressOnParent>
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Connection>UT</rasd:Connection>
+        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"</rasd:Description>
+        <rasd:ElementName>Ethernet4</rasd:ElementName>
+        <rasd:InstanceID>14</rasd:InstanceID>
         <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
""")


    def test_set_nic_kitchen_sink_no_existing(self):
        """Define NIC in an OVF that previously had none"""
        self.call_edit_hardware(['-n', '1', '-N', 'testme',
                                 '-M', '12:34:56:78:9a:bc'],
                                input=self.minimal_ovf)
        self.check_diff(file1=self.minimal_ovf,
expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">
   <ovf:References />
+  <ovf:NetworkSection>
+    <ovf:Info>Logical networks</ovf:Info>
+    <ovf:Network ovf:name="testme">
+      <ovf:Description>testme</ovf:Description>
+    </ovf:Network>
+  </ovf:NetworkSection>
   <ovf:VirtualSystem ovf:id="x">
...
       <ovf:Info />
+      <ovf:Item>
+        <rasd:Address>12:34:56:78:9a:bc</rasd:Address>
+        <rasd:Connection>testme</rasd:Connection>
+        <rasd:ElementName>Ethernet1</rasd:ElementName>
+        <rasd:InstanceID>1</rasd:InstanceID>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")


    def test_set_serial_count(self):
        """Test addition and removal of serial ports"""

        # Remove a shared serial port from a single profile
        self.call_edit_hardware(['--serial-ports', '1', '-p', '2CPU-2GB-1NIC'])
        self.check_diff(
"""
       </ovf:Item>
-      <ovf:Item ovf:required="false">
+      <ovf:Item ovf:configuration="1CPU-1GB-1NIC 4CPU-4GB-3NIC" ovf:required="false">
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
""")

        # Remove a shared serial port from all profiles
        self.call_edit_hardware(['--serial-ports', '1'])
        self.check_diff(
"""
       </ovf:Item>
-      <ovf:Item ovf:required="false">
-        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Description>Serial Port acting as IOSd Aux Port</rasd:Description>
-        <rasd:ElementName>Serial 2</rasd:ElementName>
-        <rasd:InstanceID>10</rasd:InstanceID>
-        <rasd:ResourceType>21</rasd:ResourceType>
-      </ovf:Item>
       <ovf:Item>
""")

        # Create a serial port under all profiles
        self.call_edit_hardware(['--serial-ports', '3'])
        self.check_diff(
"""
       </ovf:Item>
+      <ovf:Item ovf:required="false">
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Description>Serial Port acting as IOSd Aux Port</rasd:Description>
+        <rasd:ElementName>Serial 2</rasd:ElementName>
+        <rasd:InstanceID>14</rasd:InstanceID>
+        <rasd:ResourceType>21</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")

    def test_set_serial_count_no_existing(self):
        """Create a serial port in an OVF that doesn't have one"""
        self.call_edit_hardware(['--serial-ports', '1'], input=self.minimal_ovf)
        self.check_diff(file1=self.minimal_ovf,
expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">
   <ovf:References />
...
       <ovf:Info />
+      <ovf:Item>
+        <rasd:ElementName>serial</rasd:ElementName>
+        <rasd:InstanceID>1</rasd:InstanceID>
+        <rasd:ResourceType>21</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")


    def test_set_serial_connectivity(self):
        """Test setting and removing serial connectivity information"""

        # Set connectivity for one port under all profiles
        self.call_edit_hardware(['--serial-connectivity',
                                 'telnet://localhost:22001'])
        self.check_diff(
"""
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://localhost:22001</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
""")

        # Set connectivity for both ports under all profiles
        self.call_edit_hardware(['--serial-connectivity',
                                 'telnet://localhost:22001',
                                 'telnet://localhost:22002'])
        self.check_diff(
"""
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://localhost:22001</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
...
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://localhost:22002</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
""")


    def test_serial_kitchen_sink(self):
        """Multiple simultaneous serial changes"""

        # Add a serial and set connectivity
        self.call_edit_hardware(['--serial-ports', '3',
                                 '--serial-connectivity', 'telnet://foo:1',
                                 'telnet://foo:2', 'telnet://foo:3'])
        self.check_diff(
"""
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://foo:1</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
...
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://foo:2</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
...
         <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
+      <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://foo:3</rasd:Address>
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Description>Serial Port acting as IOSd Aux Port</rasd:Description>
+        <rasd:ElementName>Serial 2</rasd:ElementName>
+        <rasd:InstanceID>14</rasd:InstanceID>
+        <rasd:ResourceType>21</rasd:ResourceType>
       </ovf:Item>
""")

        # Delete a port and set connectivity
        self.call_edit_hardware(['-s', '1', '-S', 'telnet://bar:22'])
        self.check_diff(
"""
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://bar:22</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
...
         <rasd:InstanceID>9</rasd:InstanceID>
-        <rasd:ResourceType>21</rasd:ResourceType>
-      </ovf:Item>
-      <ovf:Item ovf:required="false">
-        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Description>Serial Port acting as IOSd Aux Port</rasd:Description>
-        <rasd:ElementName>Serial 2</rasd:ElementName>
-        <rasd:InstanceID>10</rasd:InstanceID>
         <rasd:ResourceType>21</rasd:ResourceType>
""")


    def test_set_scsi_subtype(self):
        """Test SCSI controller subtype changes"""

        # Change type under all profiles
        self.call_edit_hardware(['--scsi-subtype', 'virtio'])
        self.check_diff("""
         <rasd:InstanceID>3</rasd:InstanceID>
-        <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
+        <rasd:ResourceSubType>virtio</rasd:ResourceSubType>
         <rasd:ResourceType>6</rasd:ResourceType>
""")

        # Remove type under all profiles
        self.call_edit_hardware(['--scsi-subtype', ''])
        self.check_diff("""
         <rasd:InstanceID>3</rasd:InstanceID>
-        <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
         <rasd:ResourceType>6</rasd:ResourceType>
""")

        # Change type under one profile
        self.call_edit_hardware(['--scsi-subtype', 'virtio',
                                 '-p', '4CPU-4GB-3NIC'])
        # This requires creating a new variant of the SCSI controller
        # specific to this profile
        self.check_diff("""
       </ovf:Item>
+      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>0</rasd:Address>
+        <rasd:Description>SCSI Controller</rasd:Description>
+        <rasd:ElementName>SCSI Controller 0</rasd:ElementName>
+        <rasd:InstanceID>3</rasd:InstanceID>
+        <rasd:ResourceSubType>virtio</rasd:ResourceSubType>
+        <rasd:ResourceType>6</rasd:ResourceType>
+      </ovf:Item>
       <ovf:Item>
""")


    def test_set_scsi_subtype_no_existing(self):
        """Set SCSI subtype for an OVF with no SCSI controller (no-op)."""
        self.call_edit_hardware(['--scsi-subtype', 'virtio'],
                                input=self.minimal_ovf)
        self.check_diff("", file1=self.minimal_ovf)


    def test_set_ide_subtype(self):
        """Test IDE controller subtype changes"""

        # Change type under all profiles
        self.call_edit_hardware(['--ide-subtype', 'virtio'])
        # Since there is no pre-existing subtype, we just create it
        # under each controller:
        self.check_diff("""
         <rasd:InstanceID>4</rasd:InstanceID>
+        <rasd:ResourceSubType>virtio</rasd:ResourceSubType>
         <rasd:ResourceType>5</rasd:ResourceType>
...
         <rasd:InstanceID>5</rasd:InstanceID>
+        <rasd:ResourceSubType>virtio</rasd:ResourceSubType>
         <rasd:ResourceType>5</rasd:ResourceType>
""")

        # Change type under one profile
        self.call_edit_hardware(['--ide-subtype', 'virtio',
                                 '-p', '4CPU-4GB-3NIC'])
        # Here we have to create new controllers under this profile
        # while leaving the default alone
        self.check_diff(
"""
       </ovf:Item>
+      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>1</rasd:Address>
+        <rasd:Description>IDE Controller</rasd:Description>
+        <rasd:ElementName>VirtualIDEController 1</rasd:ElementName>
+        <rasd:InstanceID>4</rasd:InstanceID>
+        <rasd:ResourceSubType>virtio</rasd:ResourceSubType>
+        <rasd:ResourceType>5</rasd:ResourceType>
+      </ovf:Item>
       <ovf:Item>
...
         <rasd:InstanceID>5</rasd:InstanceID>
+        <rasd:ResourceType>5</rasd:ResourceType>
+      </ovf:Item>
+      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>0</rasd:Address>
+        <rasd:Description>IDE Controller</rasd:Description>
+        <rasd:ElementName>VirtualIDEController 0</rasd:ElementName>
+        <rasd:InstanceID>5</rasd:InstanceID>
+        <rasd:ResourceSubType>virtio</rasd:ResourceSubType>
         <rasd:ResourceType>5</rasd:ResourceType>
""")


    def test_set_ide_subtype_no_existing(self):
        """Set IDE subtype for an OVF with no IDE controller (no-op)."""
        self.call_edit_hardware(['--ide-subtype', 'virtio'],
                                input=self.minimal_ovf)
        self.check_diff("", file1=self.minimal_ovf)


    def test_profiles(self):
        """Test configuration profile creation"""

        # Add a profile sharing attributes with the default profile:
        self.call_edit_hardware(['--profile', 'UT', '--cpus', '1'])
        self.check_diff("""
     </ovf:Configuration>
+    <ovf:Configuration ovf:id="UT">
+      <ovf:Label>UT</ovf:Label>
+      <ovf:Description>UT</ovf:Description>
+    </ovf:Configuration>
   </ovf:DeploymentOptionSection>
""")

        # Create a new profile:
        self.call_edit_hardware(['--profile', 'UT', '--cpus', '8'])
        self.check_diff("""
     </ovf:Configuration>
+    <ovf:Configuration ovf:id="UT">
+      <ovf:Label>UT</ovf:Label>
+      <ovf:Description>UT</ovf:Description>
+    </ovf:Configuration>
   </ovf:DeploymentOptionSection>
...
       </ovf:Item>
+      <ovf:Item ovf:configuration="UT">
+        <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
+        <rasd:Description>Number of Virtual CPUs</rasd:Description>
+        <rasd:ElementName>8 virtual CPU(s)</rasd:ElementName>
+        <rasd:InstanceID>1</rasd:InstanceID>
+        <rasd:ResourceType>3</rasd:ResourceType>
+        <rasd:VirtualQuantity>8</rasd:VirtualQuantity>
+        <vmw:CoresPerSocket ovf:required="false">1</vmw:CoresPerSocket>
+      </ovf:Item>
       <ovf:Item>
""")

        # Create two new profiles:
        self.call_edit_hardware(['--profile', 'UT', 'UT2', '--memory', '8192'])
        self.check_diff(
"""
     </ovf:Configuration>
+    <ovf:Configuration ovf:id="UT">
+      <ovf:Label>UT</ovf:Label>
+      <ovf:Description>UT</ovf:Description>
+    </ovf:Configuration>
+    <ovf:Configuration ovf:id="UT2">
+      <ovf:Label>UT2</ovf:Label>
+      <ovf:Description>UT2</ovf:Description>
+    </ovf:Configuration>
   </ovf:DeploymentOptionSection>
...
       </ovf:Item>
+      <ovf:Item ovf:configuration="UT UT2">
+        <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
+        <rasd:Description>Memory Size</rasd:Description>
+        <rasd:ElementName>8192MB of memory</rasd:ElementName>
+        <rasd:InstanceID>2</rasd:InstanceID>
+        <rasd:ResourceType>4</rasd:ResourceType>
+        <rasd:VirtualQuantity>8192</rasd:VirtualQuantity>
+      </ovf:Item>
       <ovf:Item>
""")


    def test_create_profile_no_existing(self):
        """Add a profile and associated elements to an OVF that doesn't
        already have any."""

        self.call_edit_hardware(['--profile', "UT",
                                 '--nic-networks', "VM Network"],
                                input=self.minimal_ovf)
        self.check_diff(file1=self.minimal_ovf,
expected="""
   <ovf:References />
+  <ovf:DeploymentOptionSection>
+    <ovf:Info>Configuration Profiles</ovf:Info>
+    <ovf:Configuration ovf:id="UT">
+      <ovf:Label>UT</ovf:Label>
+      <ovf:Description>UT</ovf:Description>
+    </ovf:Configuration>
+  </ovf:DeploymentOptionSection>
+  <ovf:NetworkSection>
+    <ovf:Info>Logical networks</ovf:Info>
+    <ovf:Network ovf:name="VM Network">
+      <ovf:Description>VM Network</ovf:Description>
+    </ovf:Network>
+  </ovf:NetworkSection>
   <ovf:VirtualSystem ovf:id="x">
""")


class TestOVFEditProduct(COT_UT):
    """Test cases for "cot edit-product" command with OVF files"""

    def test_no_work(self):
        """Call 'cot edit-product' with no work to do"""
        self.call_cot(['edit-product', self.input_ovf], result=2)


    def call_edit_product(self, argv, result=0, input=None):
        """Call 'cot edit-product' with typical arguments"""
        if input is None:
            input = self.input_ovf
        new_argv = ['edit-product', input,
                    '-o', self.temp_file] + argv
        return self.call_cot(new_argv, result)


    def test_valid_1(self):
        """Can edit short-version in isolation"""
        for cli_opt in ['-v', '--version']:
            result = self.call_edit_product([cli_opt, '5.2.0.01I'])
            self.check_diff(
"""
       <ovf:Vendor>Cisco Systems, Inc.</ovf:Vendor>
-      <ovf:Version>DEV</ovf:Version>
+      <ovf:Version>5.2.0.01I</ovf:Version>
       <ovf:FullVersion>DEVELOPMENT IMAGE</ovf:FullVersion>
""")


    def test_valid_2(self):
        """Can edit full-version in isolation"""
        for cli_opt in ['-V', '--full-version']:
            result = self.call_edit_product([cli_opt,
                                             "Cisco IOS XRv, Version 5.2"])
            self.check_diff(
"""
       <ovf:Version>DEV</ovf:Version>
-      <ovf:FullVersion>DEVELOPMENT IMAGE</ovf:FullVersion>
+      <ovf:FullVersion>Cisco IOS XRv, Version 5.2</ovf:FullVersion>
       <ovf:ProductUrl>http://www.cisco.com/en/US/products/ps12559/index.html</ovf:ProductUrl>
""")


    def test_valid_3(self):
        """Can edit both versions together"""
        for cli_opt_1 in ['-v', '--version']:
            for cli_opt_2 in ['-V', '--full-version']:
                result = self.call_edit_product([cli_opt_1, '5.2.0.01I',
                                                 cli_opt_2,
                                                 "Cisco IOS XRv, Version 5.2"])
                self.check_diff(
"""
       <ovf:Vendor>Cisco Systems, Inc.</ovf:Vendor>
-      <ovf:Version>DEV</ovf:Version>
-      <ovf:FullVersion>DEVELOPMENT IMAGE</ovf:FullVersion>
+      <ovf:Version>5.2.0.01I</ovf:Version>
+      <ovf:FullVersion>Cisco IOS XRv, Version 5.2</ovf:FullVersion>
       <ovf:ProductUrl>http://www.cisco.com/en/US/products/ps12559/index.html</ovf:ProductUrl>
""")

    def test_valid_no_existing(self):
        """Set properties of an OVF with no previous product information"""
        self.call_edit_product(['-v', "Version", '-V', "Full Version"],
                               input=self.minimal_ovf)
        self.check_diff(file1=self.minimal_ovf,
expected="""
     </ovf:VirtualHardwareSection>
+    <ovf:ProductSection>
+      <ovf:Info>Product Information</ovf:Info>
+      <ovf:Version>Version</ovf:Version>
+      <ovf:FullVersion>Full Version</ovf:FullVersion>
+    </ovf:ProductSection>
   </ovf:VirtualSystem>
""")


class TestOVFEditProperties(COT_UT):
    """Test cases for "cot edit-properties" command with OVF files
    """

    def call_edit_properties(self, argv, result=0):
        """Call 'cot edit-properties' with typical arguments"""
        new_argv = ['edit-properties', self.input_ovf,
                    '-o', self.temp_file] + argv
        return self.call_cot(new_argv, result)

    def test_set_property_valid(self):
        """Call 'cot edit-properties' to set an existing property.
        """

        # Set one property
        self.call_edit_properties(['-p', 'login-username=admin'])
        self.check_diff(
"""
       <ovf:Category>1. Bootstrap Properties</ovf:Category>
-      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" ovf:type="string" ovf:userConfigurable="true" ovf:value="">
+      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" ovf:type="string" ovf:userConfigurable="true" ovf:value="admin">
         <ovf:Label>Login Username</ovf:Label>
""")
        # Set two properties in one go
        self.call_edit_properties(['-p', 'login-password=cisco123',
                                   'enable-ssh-server=1'])
        self.check_diff(
"""
       </ovf:Property>
-      <ovf:Property ovf:key="login-password" ovf:password="true" ovf:qualifiers="MaxLen(25)" ovf:type="string" ovf:userConfigurable="true" ovf:value="">
+      <ovf:Property ovf:key="login-password" ovf:password="true" ovf:qualifiers="MaxLen(25)" ovf:type="string" ovf:userConfigurable="true" ovf:value="cisco123">
         <ovf:Label>Login Password</ovf:Label>
...
       <ovf:Category>2. Features</ovf:Category>
-      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" ovf:userConfigurable="true" ovf:value="false">
+      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" ovf:userConfigurable="true" ovf:value="true">
         <ovf:Label>Enable SSH Login</ovf:Label>
""")

        # Create property and set its value
        self.call_edit_properties(['-p', 'new-property=hello'])
        self.check_diff(
"""
       </ovf:Property>
+      <ovf:Property ovf:key="new-property" ovf:type="string" ovf:value="hello" />
     </ovf:ProductSection>
""")

        # Create property with empty string for value
        self.call_edit_properties(['-p', 'new-property-2='])
        self.check_diff(
"""
       </ovf:Property>
+      <ovf:Property ovf:key="new-property-2" ovf:type="string" ovf:value="" />
     </ovf:ProductSection>
""")


    def test_config_file(self):
        """Inject a sequence of properties from a config file.
        """
        self.call_edit_properties(['--config-file',
                                   os.path.join(os.path.dirname(__file__),
                                                "sample_cfg.txt")])
        self.check_diff(
"""
       </ovf:Property>
+      <ovf:Property ovf:key="config-0001" ovf:type="string" ovf:value="interface GigabitEthernet0/0/0/0" />
+      <ovf:Property ovf:key="config-0002" ovf:type="string" ovf:value="no shutdown" />
+      <ovf:Property ovf:key="config-0003" ovf:type="string" ovf:value="interface Loopback0" />
+      <ovf:Property ovf:key="config-0004" ovf:type="string" ovf:value="end" />
     </ovf:ProductSection>
""")


    def test_combined(self):
        """Set individual properties AND add from a config file
        """

        self.call_edit_properties(['--config-file',
                                   os.path.join(os.path.dirname(__file__),
                                                "sample_cfg.txt"),
                                   '-p', 'login-password=cisco123',
                                   'enable-ssh-server=1'])
        self.check_diff(
"""
       </ovf:Property>
-      <ovf:Property ovf:key="login-password" ovf:password="true" ovf:qualifiers="MaxLen(25)" ovf:type="string" ovf:userConfigurable="true" ovf:value="">
+      <ovf:Property ovf:key="login-password" ovf:password="true" ovf:qualifiers="MaxLen(25)" ovf:type="string" ovf:userConfigurable="true" ovf:value="cisco123">
         <ovf:Label>Login Password</ovf:Label>
...
       <ovf:Category>2. Features</ovf:Category>
-      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" ovf:userConfigurable="true" ovf:value="false">
+      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" ovf:userConfigurable="true" ovf:value="true">
         <ovf:Label>Enable SSH Login</ovf:Label>
...
       </ovf:Property>
+      <ovf:Property ovf:key="config-0001" ovf:type="string" ovf:value="interface GigabitEthernet0/0/0/0" />
+      <ovf:Property ovf:key="config-0002" ovf:type="string" ovf:value="no shutdown" />
+      <ovf:Property ovf:key="config-0003" ovf:type="string" ovf:value="interface Loopback0" />
+      <ovf:Property ovf:key="config-0004" ovf:type="string" ovf:value="end" />
     </ovf:ProductSection>
""")


class TestOVFInfo(COT_UT):
    """Test cases for "cot info" command with OVF files"""

    def check_cot_output(self, argv, expected):
        """Invoke cot with the specified arguments, capturing stdout and
        suppressing stderr. Fail if COT returns a non-zero (error) return code,
        or if stdout does not match the expected output."""

        argv.insert(0, os.path.join(os.path.dirname(__file__),
                                    "..", "..", "bin", "cot"))
        try:
            output = check_output(argv).decode()
        except subprocess.CalledProcessError as e:
            self.fail("{0} returned {1} (error) instead of 0 (success):\n{2}"
                      .format(e.cmd, e.returncode, e.output))

        output_lines = output.splitlines()
        expected_lines = expected.splitlines()
        while (output_lines or expected_lines):
            # Compare line-by-line, but skip any whitespace-only lines
            output_line = ""
            while (output_lines and not output_line):
                output_line = output_lines.pop(0).strip()
            expected_line = ""
            while (expected_lines and not expected_line):
                expected_line = expected_lines.pop(0).strip()
            if not output_line and not expected_line:
                break # Done with both!
            if output_line != expected_line:
                self.fail("Unexpected output from {0} - "
                          "expected:\n{1}\ngot:\n{2}"
                          .format(" ".join(argv), expected, output))

    def test_minimal_ovf(self):
        """Get info for minimal OVF with no real content."""
        # For an OVF this simple, standard/brief/verbose output are the same
        expected_output="""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  None (default)                     0      0 MB      0       0   0 /       0 B
""".format(self.minimal_ovf)
        self.check_cot_output(['info', self.minimal_ovf], expected_output)

        self.check_cot_output(['info', '--brief', self.minimal_ovf],
                              expected_output)

        self.check_cot_output(['info', '--verbose', self.minimal_ovf],
                              expected_output)


    def test_multiple_minimal_ovf(self):
        """Test multiple OVFs at once"""
        self.check_cot_output(['info', self.minimal_ovf, self.minimal_ovf],
"""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  None (default)                     0      0 MB      0       0   0 /       0 B

-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  None (default)                     0      0 MB      0       0   0 /       0 B
""".format(self.minimal_ovf))


    def test_input_ovf(self):
        """Test the standard input ovf"""
        self.check_cot_output(['info', self.input_ovf],
"""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Product:  generic platform
          http://www.cisco.com/en/US/products/ps12559/index.html
Vendor:   Cisco Systems, Inc.
          http://www.cisco.com
Version:  DEV
          DEVELOPMENT IMAGE

Files and Disks:                      File Size   Capacity Device
                                     ---------- ---------- --------------------
  input.vmdk                          149.00 kB    1.00 GB harddisk @ SCSI 0:0
  input.iso                           352.00 kB            cdrom @ IDE 1:0

Hardware Variants:
  System types:             vmx-07 vmx-08
  SCSI device types:        lsilogic
  Ethernet device types:    VMXNET3

Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  4CPU-4GB-3NIC (default)            4   4.00 GB      3       2   1 /   1.00 GB
    Label:          "4 vCPUs, 4 GB RAM, 3 NICs"
    Description:    "Default hardware profile - 4 vCPUs, 4 GB RAM, 3 NICs"
  1CPU-1GB-1NIC                      1   1.00 GB      1       2   1 /   1.00 GB
    Label:          "1 vCPU, 1 GB RAM, 1 NIC"
    Description:    "Minimal hardware profile - 1 vCPU, 1 GB RAM, 1 NIC"
  2CPU-2GB-1NIC                      2   2.00 GB      1       2   1 /   1.00 GB
    Label:          "2 vCPUs, 2 GB RAM, 1 NIC"
    Description:    "Minimal hardware profile - 2 vCPUs, 2 GB RAM, 1 NIC"

Networks:
  VM Network

NICs and Associated Networks:
  GigabitEthernet1               : VM Network
  GigabitEthernet2               : VM Network
  GigabitEthernet3               : VM Network

Properties:
  login-username                 :
      "Login Username"
  login-password                 :
      "Login Password"
  mgmt-ipv4-addr                 :
      "Management IPv4 Address/Mask"
  mgmt-ipv4-gateway              :
      "Management IPv4 Default Gateway"
  hostname                       :
      "Router Name"
  enable-ssh-server              : false
      "Enable SSH Login"
  enable-http-server             : false
      "Enable HTTP Server"
  enable-https-server            : false
      "Enable HTTPS Server"
  privilege-password             :
      "Enable Password"
  domain-name                    :
      "Domain Name"
""".format(self.input_ovf))

        self.check_cot_output(['info', '--brief', self.input_ovf],
"""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Product:  generic platform
Vendor:   Cisco Systems, Inc.
Version:  DEV

Files and Disks:                      File Size   Capacity Device
                                     ---------- ---------- --------------------
  input.vmdk                          149.00 kB    1.00 GB harddisk @ SCSI 0:0
  input.iso                           352.00 kB            cdrom @ IDE 1:0

Hardware Variants:
  System types:             vmx-07 vmx-08
  SCSI device types:        lsilogic
  Ethernet device types:    VMXNET3

Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  4CPU-4GB-3NIC (default)            4   4.00 GB      3       2   1 /   1.00 GB
  1CPU-1GB-1NIC                      1   1.00 GB      1       2   1 /   1.00 GB
  2CPU-2GB-1NIC                      2   2.00 GB      1       2   1 /   1.00 GB

Networks:
  VM Network

Properties:
  login-username                 :
  login-password                 :
  mgmt-ipv4-addr                 :
  mgmt-ipv4-gateway              :
  hostname                       :
  enable-ssh-server              : false
  enable-http-server             : false
  enable-https-server            : false
  privilege-password             :
  domain-name                    :
""".format(self.input_ovf))

        self.check_cot_output(['info', '--verbose', self.input_ovf],
"""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Product:  generic platform
          http://www.cisco.com/en/US/products/ps12559/index.html
Vendor:   Cisco Systems, Inc.
          http://www.cisco.com
Version:  DEV
          DEVELOPMENT IMAGE

Files and Disks:                      File Size   Capacity Device
                                     ---------- ---------- --------------------
  input.vmdk                          149.00 kB    1.00 GB harddisk @ SCSI 0:0
  input.iso                           352.00 kB            cdrom @ IDE 1:0

Hardware Variants:
  System types:             vmx-07 vmx-08
  SCSI device types:        lsilogic
  Ethernet device types:    VMXNET3

Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  4CPU-4GB-3NIC (default)            4   4.00 GB      3       2   1 /   1.00 GB
    Label:          "4 vCPUs, 4 GB RAM, 3 NICs"
    Description:    "Default hardware profile - 4 vCPUs, 4 GB RAM, 3 NICs"
  1CPU-1GB-1NIC                      1   1.00 GB      1       2   1 /   1.00 GB
    Label:          "1 vCPU, 1 GB RAM, 1 NIC"
    Description:    "Minimal hardware profile - 1 vCPU, 1 GB RAM, 1 NIC"
  2CPU-2GB-1NIC                      2   2.00 GB      1       2   1 /   1.00 GB
    Label:          "2 vCPUs, 2 GB RAM, 1 NIC"
    Description:    "Minimal hardware profile - 2 vCPUs, 2 GB RAM, 1 NIC"

Networks:
  VM Network                     VM Network

NICs and Associated Networks:
  GigabitEthernet1               : VM Network
    VMXNET3 ethernet adapter on "VM Network"
  GigabitEthernet2               : VM Network
    VMXNET3 ethernet adapter on "VM Network"
  GigabitEthernet3               : VM Network
    VMXNET3 ethernet adapter on "VM Network"

Properties:
  login-username                 :
      "Login Username"
      Username for remote login
  login-password                 :
      "Login Password"
      Password for remote login.
      WARNING: While this password will be stored securely within IOS, the
      plain-text password will be recoverable from the OVF descriptor file.
  mgmt-ipv4-addr                 :
      "Management IPv4 Address/Mask"
      IPv4 address and mask for management interface (such as "10.1.1.100/24"
      or "10.1.1.100 255.255.255.0"), or "dhcp" to configure via DHCP
  mgmt-ipv4-gateway              :
      "Management IPv4 Default Gateway"
      IPv4 default gateway address (such as "10.1.1.1") for management
      interface, or "dhcp" to configure via DHCP
  hostname                       :
      "Router Name"
      Hostname of this router
  enable-ssh-server              : false
      "Enable SSH Login"
      Enable remote login via SSH and disable remote login via telnet. Requires
      login-username and login-password to be set!
  enable-http-server             : false
      "Enable HTTP Server"
      Enable HTTP server capability for REST API
  enable-https-server            : false
      "Enable HTTPS Server"
      Enable HTTPS server capability for REST API
  privilege-password             :
      "Enable Password"
      Password for privileged (enable) access.
      WARNING: While this password will be stored securely within IOS, the
      plain-text password will be recoverable from the OVF descriptor file.
  domain-name                    :
      "Domain Name"
      Network domain name (such as "cisco.com")
""".format(self.input_ovf))


    def test_iosv_ovf(self):
        """Test an IOSv OVF.
        """
        self.check_cot_output(['info', '--brief', self.iosv_ovf],
"""
-------------------------------------------------------------------------------
{0}
COT detected platform type: Cisco IOSv
-------------------------------------------------------------------------------
Product:  Cisco IOSv Virtual Router
Vendor:   Cisco Systems, Inc.
Version:  15.4(2.4)T

Files and Disks:                      File Size   Capacity Device
                                     ---------- ---------- --------------------
  input.vmdk                          149.00 kB    1.00 GB harddisk @ IDE 0:0
  (disk placeholder)                         --  128.00 MB harddisk @ IDE 0:1

Hardware Variants:
  System types:             vmx-08 Cisco:Internal:VMCloud-01
  IDE device types:         virtio
  Ethernet device types:    E1000

Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  1CPU-384MB-2NIC (default)          1    384 MB      2       2   2 /   1.12 GB
  1CPU-1GB-8NIC                      1    384 MB      8       2   2 /   1.12 GB
  1CPU-3GB-10NIC                     1    384 MB     10       2   2 /   1.12 GB
  1CPU-3GB-16NIC                     1    384 MB     16       2   2 /   1.12 GB

Networks:
  GigabitEthernet0_0
  GigabitEthernet0_1
  GigabitEthernet0_2
  GigabitEthernet0_3
  GigabitEthernet0_4
  GigabitEthernet0_5
  GigabitEthernet0_6
  GigabitEthernet0_7
  GigabitEthernet0_8
  GigabitEthernet0_9
  GigabitEthernet0_10
  GigabitEthernet0_11
  GigabitEthernet0_12
  GigabitEthernet0_13
  GigabitEthernet0_14
  GigabitEthernet0_15
""".format(self.iosv_ovf))

        self.check_cot_output(['info', '--verbose', self.iosv_ovf],
"""
-------------------------------------------------------------------------------
{0}
COT detected platform type: Cisco IOSv
-------------------------------------------------------------------------------
Product:  Cisco IOSv Virtual Router
          http://www.cisco.com/en/US/products/index.html
Vendor:   Cisco Systems, Inc.
          http://www.cisco.com
Version:  15.4(2.4)T
          Cisco IOS Software, IOSv Software (VIOS-ADVENTERPRISEK9-M), Version 15.4(2.4)T,  ENGINEERING WEEKLY BUILD, synced to  V153_3_M1_9

Files and Disks:                      File Size   Capacity Device
                                     ---------- ---------- --------------------
  input.vmdk                          149.00 kB    1.00 GB harddisk @ IDE 0:0
  (disk placeholder)                         --  128.00 MB harddisk @ IDE 0:1

Hardware Variants:
  System types:             vmx-08 Cisco:Internal:VMCloud-01
  IDE device types:         virtio
  Ethernet device types:    E1000

Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  1CPU-384MB-2NIC (default)          1    384 MB      2       2   2 /   1.12 GB
    Label:          "Small"
    Description:    "Minimal hardware profile - 1 vCPU, 384 MB RAM, 2 NICs"
  1CPU-1GB-8NIC                      1    384 MB      8       2   2 /   1.12 GB
    Label:          "Medium"
    Description:    "Medium hardware profile - 1 vCPU, 1 GB RAM, 8 NICs"
  1CPU-3GB-10NIC                     1    384 MB     10       2   2 /   1.12 GB
    Label:          "Large (ESXi)"
    Description:    "Large hardware profile for ESXi - 1 vCPU, 3 GB RAM, 10
                     NICs"
  1CPU-3GB-16NIC                     1    384 MB     16       2   2 /   1.12 GB
    Label:          "Large (non-ESXi)"
    Description:    "Large hardware profile for other hypervisors - 1 vCPU, 3
                     GB RAM, 16 NICs. (Note: ESXi only permits 10 NICs in a VM
                     so this profile is unsupported on ESXi.)"

Networks:
  GigabitEthernet0_0             Data network 1
  GigabitEthernet0_1             Data network 2
  GigabitEthernet0_2             Data network 3
  GigabitEthernet0_3             Data network 4
  GigabitEthernet0_4             Data network 5
  GigabitEthernet0_5             Data network 6
  GigabitEthernet0_6             Data network 7
  GigabitEthernet0_7             Data network 8
  GigabitEthernet0_8             Data network 9
  GigabitEthernet0_9             Data network 10
  GigabitEthernet0_10            Data network 11
  GigabitEthernet0_11            Data network 12
  GigabitEthernet0_12            Data network 13
  GigabitEthernet0_13            Data network 14
  GigabitEthernet0_14            Data network 15
  GigabitEthernet0_15            Data network 16

NICs and Associated Networks:
  GigabitEthernet0/0             : GigabitEthernet0_0
    NIC representing GigabitEthernet0/0 interface
  GigabitEthernet0/1             : GigabitEthernet0_1
    NIC representing GigabitEthernet0/1 interface
  GigabitEthernet0/2             : GigabitEthernet0_2
    NIC representing GigabitEthernet0/2 interface
  GigabitEthernet0/3             : GigabitEthernet0_3
    NIC representing GigabitEthernet0/3 interface
  GigabitEthernet0/4             : GigabitEthernet0_4
    NIC representing GigabitEthernet0/4 interface
  GigabitEthernet0/5             : GigabitEthernet0_5
    NIC representing GigabitEthernet0/5 interface
  GigabitEthernet0/6             : GigabitEthernet0_6
    NIC representing GigabitEthernet0/6 interface
  GigabitEthernet0/7             : GigabitEthernet0_7
    NIC representing GigabitEthernet0/7 interface
  GigabitEthernet0/8             : GigabitEthernet0_8
    NIC representing GigabitEthernet0/8 interface
  GigabitEthernet0/9             : GigabitEthernet0_9
    NIC representing GigabitEthernet0/9 interface
  GigabitEthernet0/10            : GigabitEthernet0_10
    NIC representing GigabitEthernet0/10 interface
  GigabitEthernet0/11            : GigabitEthernet0_11
    NIC representing GigabitEthernet0/11 interface
  GigabitEthernet0/12            : GigabitEthernet0_12
    NIC representing GigabitEthernet0/12 interface
  GigabitEthernet0/13            : GigabitEthernet0_13
    NIC representing GigabitEthernet0/13 interface
  GigabitEthernet0/14            : GigabitEthernet0_14
    NIC representing GigabitEthernet0/14 interface
  GigabitEthernet0/15            : GigabitEthernet0_15
    NIC representing GigabitEthernet0/15 interface
""".format(self.iosv_ovf))


    def test_v09_ovf(self):
        """Test a legacy v0.9 OVF.
        """
        self.check_cot_output(['info', self.v09_ovf],
"""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Annotation: Hello world! This is a version 0.9 OVF.

Files and Disks:                      File Size   Capacity Device
                                     ---------- ---------- --------------------
  input.vmdk                          149.00 kB    1.00 GB harddisk @ SCSI 0:0

Hardware Variants:
  System types:             vmx-04
  SCSI device types:        lsilogic
  Ethernet device types:    PCNet32

Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  None (default)                     1   8.00 GB      1       0   1 /   1.00 GB

Networks:
  bridged

NICs and Associated Networks:
  ethernet0                      : bridged
""".format(self.v09_ovf))

        self.check_cot_output(['info', '--verbose', self.v09_ovf],
"""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Annotation: Hello world! This is a version 0.9 OVF.

Files and Disks:                      File Size   Capacity Device
                                     ---------- ---------- --------------------
  input.vmdk                          149.00 kB    1.00 GB harddisk @ SCSI 0:0

Hardware Variants:
  System types:             vmx-04
  SCSI device types:        lsilogic
  Ethernet device types:    PCNet32

Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  None (default)                     1   8.00 GB      1       0   1 /   1.00 GB

Networks:
  bridged                        The bridged network

NICs and Associated Networks:
  ethernet0                      : bridged
    PCNet32 ethernet adapter
""".format(self.v09_ovf))


    def test_vmware_ovf(self):
        """Test info string for an OVF with lots of VMware custom extensions.
        """
        self.check_cot_output(['info', self.vmware_ovf],
"""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Files and Disks:                      File Size   Capacity Device
                                     ---------- ---------- --------------------
  input.vmdk                          149.00 kB    1.00 GB harddisk @ SCSI 0:0

Hardware Variants:
  System types:             vmx-08
  SCSI device types:        virtio lsilogic
  Ethernet device types:    E1000

Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  None (default)                     2   1.50 GB      4       0   1 /   1.00 GB

Networks:
  lanethernet0

NICs and Associated Networks:
  Network adapter 1              : lanethernet0
  Network adapter 2              : lanethernet0
  Network adapter 3              : lanethernet0
  Network adapter 4              : lanethernet0
""".format(self.vmware_ovf))

        self.check_cot_output(['info', '--verbose', self.vmware_ovf],
"""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Files and Disks:                      File Size   Capacity Device
                                     ---------- ---------- --------------------
  input.vmdk                          149.00 kB    1.00 GB harddisk @ SCSI 0:0

Hardware Variants:
  System types:             vmx-08
  SCSI device types:        virtio lsilogic
  Ethernet device types:    E1000

Configuration Profiles:           CPUs    Memory   NICs Serials  Disks/Capacity
                                  ---- --------- ------ ------- ---------------
  None (default)                     2   1.50 GB      4       0   1 /   1.00 GB

Networks:
  lanethernet0                   The lanethernet0 network

NICs and Associated Networks:
  Network adapter 1              : lanethernet0
    E1000 ethernet adapter on "lanethernet0"
  Network adapter 2              : lanethernet0
    E1000 ethernet adapter on "lanethernet0"
  Network adapter 3              : lanethernet0
    E1000 ethernet adapter on "lanethernet0"
  Network adapter 4              : lanethernet0
    E1000 ethernet adapter on "lanethernet0"
""".format(self.vmware_ovf))


class TestOVFInjectConfig(COT_UT):
    """Test cases for "cot inject-config" command with OVF files"""

    def setUp(self):
        """Test case setup function called automatically before each test"""
        self.config_file = os.path.join(os.path.dirname(__file__),
                                        "sample_cfg.txt")
        super(TestOVFInjectConfig, self).setUp()


    def test_no_work(self):
        """Call 'cot inject-config' with no work to do"""
        self.call_cot(['inject-config', self.input_ovf], result=2)


    def test_inject_config_iso(self):
        """Call 'cot inject-config' to inject config file on an ISO"""
        self.call_cot(['inject-config', '-c', self.config_file,
                      '-o', self.temp_file, self.input_ovf])

        self.check_diff(
"""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="config.iso" ovf:id="config.iso" ovf:size="{config_size}" />
   </ovf:References>
...
         <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>CD-ROM 2</rasd:ElementName>
+        <rasd:HostResource>ovf:/file/config.iso</rasd:HostResource>
         <rasd:InstanceID>8</rasd:InstanceID>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           config_size=os.path.getsize(os.path.join(self.temp_dir,
                                                    'config.iso'))))


    def test_inject_config_vmdk(self):
        """Call 'cot inject-config' to inject config file on a VMDK"""
        self.call_cot(['inject-config', '-c', self.config_file,
                       '-o', self.temp_file, self.iosv_ovf])

        # Note that in this case there is an existing placeholder Disk;
        # to be OVF standard compliant, the new File must be created in the
        # same order relative to the other Files as the existing Disk is
        # to the other Disks.
        self.check_diff(file1=self.iosv_ovf,
expected="""
   <ovf:References>
+    <ovf:File ovf:href="config.vmdk" ovf:id="config.vmdk" ovf:size="{config_size}" />
     <ovf:File ovf:href="input.vmdk" ovf:id="vios-adventerprisek9-m.vmdk" ovf:size="{input_size}" />
...
     <ovf:Info>Virtual disk information</ovf:Info>
-    <ovf:Disk ovf:capacity="128" ovf:capacityAllocationUnits="byte * 2^20" ovf:diskId="flash2" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
+    <ovf:Disk ovf:capacity="8" ovf:capacityAllocationUnits="byte * 2^20" ovf:diskId="flash2" ovf:fileRef="config.vmdk" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
     <ovf:Disk ovf:capacity="1073741824" ovf:capacityAllocationUnits="byte" ovf:diskId="vios-adventerprisek9-m.vmdk" ovf:fileRef="vios-adventerprisek9-m.vmdk" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
...
         <rasd:AddressOnParent>1</rasd:AddressOnParent>
-        <rasd:Description>Disk device corresponding to flash2:; may be used for bootstrap configuration.</rasd:Description>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>flash2</rasd:ElementName>
""".format(input_size=self.FILE_SIZE['input.vmdk'],
           config_size=os.path.getsize(os.path.join(self.temp_dir, 'config.vmdk'))))

    def test_inject_config_secondary_unsupported(self):
        """inject-config for a secondary file, platform doesn't support it"""
        self.call_cot(['inject-config', "--secondary-config-file",
                       self.config_file, "-o", self.temp_file,
                       self.input_ovf], result=2)


    def test_inject_config_repeatedly(self):
        """inject-config repeatedly"""
        # Add initial config file
        self.call_cot(['inject-config', self.input_ovf, '-o', self.temp_file,
                       '-c', self.config_file])
        # Overwrite it with a new one
        self.call_cot(['inject-config', self.temp_file,
                       '-c', self.config_file])
        # And again.
        self.call_cot(['inject-config', self.temp_file,
                       '-c', self.config_file])
        self.check_diff(
"""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="config.iso" ovf:id="config.iso" ovf:size="{config_size}" />
   </ovf:References>
...
         <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>CD-ROM 2</rasd:ElementName>
+        <rasd:HostResource>ovf:/file/config.iso</rasd:HostResource>
         <rasd:InstanceID>8</rasd:InstanceID>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           config_size=os.path.getsize(os.path.join(self.temp_dir,
                                                    'config.iso'))))
