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
import sys
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
            if (ext == '.mf' or ext == '.ovf') and sys.hexversion < 0x02070000:
                # OVF changes due to 2.6 XML handling, and MF changes due to
                # checksum difference for the OVF
                print("'{0}' file comparison skipped due to "
                      "old Python version ({1})".format(ext, sys.version))
                continue
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

        # TODO - keep this one for now as it exercises the nargs/append logic
        # Set several properties in one go
        # This can be done either with multiple -p arguments or
        # a single -p with multiple key-value pairs - try 'em both and more.
        for args in (['-p', 'login-username=admin', # Individual
                      '-p', 'login-password=cisco123',
                      '-p', 'enable-ssh-server=1'],
                     ['-p', 'login-username=admin', # All for one
                            'login-password=cisco123',
                            'enable-ssh-server=1'],
                     ['-p', 'login-username=admin', # Mixed!
                      '-p', 'login-password=cisco123',
                            'enable-ssh-server=1'],
                     ['-p', 'login-username=admin', # Differently mixed!
                            'login-password=cisco123',
                      '-p', 'enable-ssh-server=1']):
            self.call_edit_properties(args)
            self.check_diff(
"""
       <ovf:Category>1. Bootstrap Properties</ovf:Category>
-      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" ovf:type="string" ovf:userConfigurable="true" ovf:value="">
+      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" ovf:type="string" ovf:userConfigurable="true" ovf:value="admin">
         <ovf:Label>Login Username</ovf:Label>
...
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


class TestOVFInfo(COT_UT):
    """Test cases for "cot info" command with OVF files"""

    def check_cot_output(self, argv, expected):
        """Invoke cot with the specified arguments, capturing stdout and
        suppressing stderr. Fail if COT returns a non-zero (error) return code,
        or if stdout does not match the expected output."""

        argv = ['python', os.path.join(os.path.dirname(__file__),
                                    "..", "..", "bin", "cot")] + argv
        try:
            output = check_output(argv, suppress_stderr=True)
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

