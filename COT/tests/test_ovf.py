#!/usr/bin/env python
#
# ovf.py - Unit test cases for COT OVF/OVA handling
#
# September 2013, Glenn F. Matthews
# Copyright (c) 2013-2015 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for COT.ovf.OVF and COT.ovf.OVFItem classes."""

import filecmp
import os
import os.path
import platform
import tempfile
import shutil
import subprocess
import xml.etree.ElementTree as ET
import sys
import tarfile
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from contextlib import closing

from COT.tests.ut import COT_UT
from COT.ovf import OVF, OVFNameHelper, OVFItem
from COT.ovf import byte_count, byte_string, factor_bytes
from COT.vm_description import VMInitError
from COT.data_validation import ValueUnsupportedError
from COT.helpers import HelperError
from COT.vm_context_manager import VMContextManager


class TestByteString(unittest.TestCase):
    """Test cases for byte-count to string conversion functions."""

    def test_byte_count(self):
        """Test byte_count() function."""
        self.assertEqual(byte_count("128", "byte"), 128)
        self.assertEqual(byte_count("1", "byte * 2^10"), 1024)

    def test_factor_bytes(self):
        """Test factor_bytes() function."""
        self.assertEqual(factor_bytes("2147483648"), ("2", "byte * 2^30"))
        self.assertEqual(factor_bytes(2147483649), ("2147483649", "byte"))

    def test_byte_string(self):
        """Test byte_string() function."""
        self.assertEqual(byte_string(1024), "1.00 kB")
        self.assertEqual(byte_string(250691584), "239.08 MB")
        self.assertEqual(byte_string(2560, base_shift=2), "2.50 GB")
        self.assertEqual(byte_string(512, base_shift=2), "512 MB")


class TestOVFInputOutput(COT_UT):
    """Test cases for OVF file input/output."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestOVFInputOutput, self).setUp()
        # Additional temp directory used by some test cases
        self.staging_dir = None

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        if self.staging_dir:
            shutil.rmtree(self.staging_dir)
        super(TestOVFInputOutput, self).tearDown()

    def test_filename_validation(self):
        """Test class method(s) for filename validation."""
        self.assertEqual('.ovf', OVF.detect_type_from_name("/foo/bar/foo.ovf"))
        self.assertEqual('.ova', OVF.detect_type_from_name("/foo/bar/foo.ova"))
        # Lazy filenames should be OK too
        self.assertEqual('.ovf',
                         OVF.detect_type_from_name("/foo/bar/foo.ovf.5.2.2"))
        self.assertLogged(levelname='WARNING',
                          msg="found '.ovf' in mid-filename; treating as such")
        self.assertEqual('.ova',
                         OVF.detect_type_from_name("/foo/bar/foo.ova.15.4.T"))
        self.assertLogged(levelname='WARNING',
                          msg="found '.ova' in mid-filename; treating as such")
        # Unsupported formats
        self.assertRaises(ValueUnsupportedError, OVF.detect_type_from_name,
                          "/foo/bar.ovf/baz")
        self.assertRaises(ValueUnsupportedError, OVF.detect_type_from_name,
                          "/foo/bar.zip")

    def test_input_output(self):
        """Read an OVF then write it again, verify no changes."""
        with VMContextManager(self.input_ovf, self.temp_file):
            pass
        self.check_diff('')

        # Filename output too
        with VMContextManager(self.input_ovf, self.temp_file + '.a.b.c'):
            self.assertLogged(
                levelname='WARNING',
                msg="found '.ovf' in mid-filename; treating as such")
            pass
        self.check_diff('', file2=(self.temp_file + ".a.b.c"))

    def test_input_output_v09(self):
        """Test reading/writing of a v0.9 OVF."""
        with VMContextManager(self.v09_ovf, self.temp_file):
            pass
        self.check_diff('', file1=self.v09_ovf)

    def test_input_output_v20_vbox(self):
        """Test reading/writing of a v2.0 OVF from VirtualBox."""
        with VMContextManager(self.v20_vbox_ovf, self.temp_file):
            pass

        # TODO - vbox XML is not very clean so the diffs are large...
        # self.check_diff('', file1=self.v20_vbox_ovf)

        # ovftool does not consider vbox ovfs to be valid
        self.validate_output_with_ovftool = False

    def test_input_output_vmware(self):
        """Test reading/writing of an OVF with custom extensions."""
        with VMContextManager(self.vmware_ovf, self.temp_file):
            pass
        # VMware disagrees with COT on some fiddly details of XML formatting
        self.check_diff("""
-<?xml version="1.0" encoding="UTF-8"?>
-<ovf:Envelope vmw:buildId="build-880146" \
xmlns="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:cim="http://schemas.dmtf.org/wbem/wscim/1/common" \
xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_ResourceAllocationSettingData" \
xmlns:vmw="http://www.vmware.com/schema/ovf" \
xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_VirtualSystemSettingData" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
+<?xml version='1.0' encoding='utf-8'?>
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_ResourceAllocationSettingData" \
xmlns:vmw="http://www.vmware.com/schema/ovf" \
xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_VirtualSystemSettingData" vmw:buildId="build-880146">
   <ovf:References>
...
   </ovf:VirtualSystem>
-</ovf:Envelope>        
+</ovf:Envelope>""", file1=self.vmware_ovf)  # noqa - trailing whitespace above

    def test_input_output_missing_file(self):
        """Test reading/writing of an OVF with missing file references."""
        # Read OVF, write OVF - make sure invalid file reference is removed
        self.staging_dir = tempfile.mkdtemp(prefix="cot_ut_ovfio_stage")
        shutil.copy(self.input_ovf, self.staging_dir)
        shutil.copy(self.input_vmdk, self.staging_dir)
        # Don't copy input.iso to the staging directory.
        with VMContextManager(os.path.join(self.staging_dir, 'input.ovf'),
                              self.temp_file):
            self.assertLogged(**self.NONEXISTENT_FILE)
        self.assertLogged(**self.REMOVING_FILE)
        self.check_diff("""
     <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="152576" />
-    <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="360448" />
   </ovf:References>
""")

        # Read-only OVF
        with VMContextManager(os.path.join(self.staging_dir, 'input.ovf'),
                              None):
            self.assertLogged(**self.NONEXISTENT_FILE)

        # File exists at read time but has disappeared by write time
        shutil.copy(self.input_iso, self.staging_dir)
        with VMContextManager(os.path.join(self.staging_dir, 'input.ovf'),
                              self.temp_file):
            os.remove(os.path.join(self.staging_dir, 'input.iso'))
        self.assertLogged(**self.FILE_DISAPPEARED)
        self.assertLogged(**self.REMOVING_FILE)
        self.check_diff("""
     <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="152576" />
-    <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="360448" />
   </ovf:References>
""")

        # Read OVA, write OVF
        try:
            tarf = tarfile.open(os.path.join(self.staging_dir, 'input.ova'),
                                'w')
            tarf.add(os.path.join(self.staging_dir, 'input.ovf'), 'input.ovf')
            tarf.add(os.path.join(self.staging_dir, 'input.vmdk'),
                     'input.vmdk')
        finally:
            tarf.close()
        with VMContextManager(
                os.path.join(self.staging_dir, 'input.ova'),
                os.path.join(self.temp_dir, 'output.ovf')):
            self.assertLogged(**self.NONEXISTENT_FILE)
        self.assertLogged(**self.REMOVING_FILE)
        self.check_diff(file2=os.path.join(self.temp_dir, 'output.ovf'),
                        expected="""
     <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="152576" />
-    <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="360448" />
   </ovf:References>
""")

        # Also test read-only OVA logic:
        with VMContextManager(os.path.join(self.staging_dir, "input.ova"),
                              None):
            self.assertLogged(**self.NONEXISTENT_FILE)

    def test_input_output_bad_file(self):
        """Test reading/writing of an OVF with incorrect file references."""
        self.staging_dir = tempfile.mkdtemp(prefix="cot_ut_ovfio_stage")
        input_dir = os.path.dirname(self.input_ovf)
        shutil.copy(os.path.join(input_dir, 'input.ovf'), self.staging_dir)
        shutil.copy(os.path.join(input_dir, 'input.iso'), self.staging_dir)
        # Copy blank.vmdk to input.vmdk so as to have the wrong size/checksum
        shutil.copy(self.blank_vmdk,
                    os.path.join(self.staging_dir, 'input.vmdk'))
        with VMContextManager(os.path.join(self.staging_dir, 'input.ovf'),
                              os.path.join(self.temp_dir, "temp.ova")):
            pass
        self.assertLogged(msg="Size of file.*seems to have changed.*"
                          "The updated OVF will reflect this change.")
        self.assertLogged(msg="Capacity of disk.*seems to have changed.*"
                          "The updated OVF will reflect this change.")

        # Write out to OVA (which will correct the file size information)

        # Now read in the OVA
        with VMContextManager(os.path.join(self.temp_dir, "temp.ova"),
                              os.path.join(self.temp_dir, "temp.ovf")):
            # Replace the tar file fake .vmdk with the real .vmdk
            tarf = tarfile.open(os.path.join(self.temp_dir, "temp.ova"), 'a')
            tarf.add(self.input_vmdk, 'input.vmdk')
            tarf.close()
        self.assertLogged(msg="Size of file.*seems to have changed.*"
                          "The updated OVF will reflect this change.")
        # TODO: When the disk is in the input OVA we can't validate capacity.
        # self.assertLogged(msg="Capacity of disk.*seems to have changed.*"
        #                  "The updated OVF will reflect this change.")

    def test_tar_untar(self):
        """Output OVF to OVA and vice versa."""
        # Read OVF and write to OVA
        ovf = OVF(self.input_ovf,
                  os.path.join(self.temp_dir, "temp.ova"))
        ovf.write()
        ovf.destroy()
        # Read OVA and write to OVF
        ovf2 = OVF(os.path.join(self.temp_dir, "temp.ova"),
                   os.path.join(self.temp_dir, "input.ovf"))
        ovf2.write()
        ovf2.destroy()

        # Make sure everything propagated over successfully
        input_dir = os.path.dirname(self.input_ovf)
        for ext in ['.ovf', '.mf', '.iso', '.vmdk']:
            if (ext == '.mf' or ext == '.ovf') and sys.hexversion < 0x02070000:
                # OVF changes due to 2.6 XML handling, and MF changes due to
                # checksum difference for the OVF
                print("'{0}' file comparison skipped due to "
                      "old Python version ({1})"
                      .format(ext, platform.python_version()))
                continue
            self.assertTrue(
                filecmp.cmp(os.path.join(input_dir, "input" + ext),
                            os.path.join(self.temp_dir, "input" + ext)),
                "{0} file changed after OVF->OVA->OVF conversion"
                .format(ext))

    def test_tar_links(self):
        """Check that OVA dereferences symlinks and hard links."""
        self.staging_dir = tempfile.mkdtemp(prefix="cot_ut_ovfio_stage")
        shutil.copy(self.input_ovf, self.staging_dir)
        # Hardlink self.input_vmdk to the staging dir
        os.link(self.input_vmdk, os.path.join(self.staging_dir, 'input.vmdk'))
        # Symlink self.input_iso to the staging dir
        os.symlink(self.input_iso, os.path.join(self.staging_dir, 'input.iso'))
        ovf = OVF(os.path.join(self.staging_dir, 'input.ovf'),
                  os.path.join(self.temp_dir, 'input.ova'))
        ovf.write()
        ovf.destroy()

        with closing(tarfile.open(os.path.join(self.temp_dir, 'input.ova'),
                                  'r')) as tarf:
            vmdk = tarf.getmember('input.vmdk')
            self.assertTrue(vmdk.isfile(),
                            "hardlink was not added as a regular file")
            self.assertFalse(vmdk.islnk())
            iso = tarf.getmember('input.iso')
            self.assertTrue(iso.isfile(),
                            "symlink was not added as a regular file")
            self.assertFalse(iso.issym())

    def test_invalid_ovf_file(self):
        """Check that various invalid input OVF files result in VMInitError."""
        fake_file = os.path.join(self.temp_dir, "foo.ovf")
        # .ovf that is an empty file
        with open(fake_file, 'w') as f:
            f.write("")
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ovf that isn't actually XML at all
        with open(fake_file, 'w') as f:
            f.write("< hello world!")
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ovf that is XML but not OVF XML
        with open(fake_file, 'w') as f:
            f.write("<?xml version='1.0' encoding='utf-8'?>")
        self.assertRaises(VMInitError, OVF, fake_file, None)
        with open(fake_file, 'w') as f:
            f.write("<?xml version='1.0' encoding='utf-8'?>")
            f.write("<foo/>")
        self.assertRaises(VMInitError, OVF, fake_file, None)

    def test_invalid_ova_file(self):
        """Check that various invalid input OVA files result in VMInitError."""
        fake_file = os.path.join(self.temp_dir, "foo.ova")
        # .ova that is an empty file
        with open(fake_file, 'w') as f:
            f.write("")
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ova that is not a TAR file
        with open(fake_file, 'w') as f:
            f.write("< hello world!")
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ova that is an empty TAR file
        tarf = tarfile.open(fake_file, 'w')
        tarf.close()
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ova that is a TAR file but does not contain an OVF descriptor
        tarf = tarfile.open(fake_file, 'w')
        try:
            tarf.add(self.blank_vmdk, os.path.basename(self.blank_vmdk))
        finally:
            tarf.close()
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ova that contains an OVF descriptor but in the wrong position
        tarf = tarfile.open(fake_file, 'a')
        try:
            tarf.add(self.input_ovf, os.path.basename(self.input_ovf))
        finally:
            tarf.close()
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ova with unsafe absolute path references
        tarf = tarfile.open(fake_file, 'w')
        try:
            # tarfile.add() is sometimes smart enough to protect us against
            # such unsafe references, but we can overrule it by using
            # gettarinfo() and addfile() instead of just add().
            tari = tarf.gettarinfo(self.minimal_ovf)
            tari.name = os.path.abspath(
                os.path.join(os.path.dirname(self.minimal_ovf),
                             "..", "..", "..",
                             os.path.basename(self.minimal_ovf)))
            with open(self.minimal_ovf, 'rb') as f:
                tarf.addfile(tari, f)
        finally:
            tarf.close()
        self.assertRaises(VMInitError, OVF, fake_file, None)

    def test_invalid_ovf_contents(self):
        """Check for rejection of OVF files with valid XML but invalid data."""
        # Multiple Items under same profile with same InstanceID
        fake_file = os.path.join(self.temp_dir, "foo.ovf")
        with open(fake_file, "w") as f:
            subprocess.check_call(['sed', 's/InstanceID>11</InstanceID>10</',
                                   self.input_ovf],
                                  stdout=f)
        if self.OVFTOOL.path:
            # Make sure ovftool also sees this as invalid
            self.assertRaises(HelperError,
                              self.OVFTOOL.validate_ovf, fake_file)
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # Item referencing a nonexistent Configuration
        with open(fake_file, "w") as f:
            subprocess.check_call(['sed', 's/on="2CPU-2GB-1NIC"/on="foo"/',
                                   self.input_ovf],
                                  stdout=f)
        if self.OVFTOOL.path:
            # Make sure ovftool also sees this as invalid
            self.assertRaises(HelperError,
                              self.OVFTOOL.validate_ovf, fake_file)
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # TODO - inconsistent order of File versus Disk?
        # TODO - Sections in wrong order?

    def test_configuration_profiles(self):
        """Check profile id list APIs."""
        # No profiles defined
        with VMContextManager(self.vmware_ovf, None) as ovf:
            self.assertEqual(ovf.config_profiles, [])
            self.assertEqual(ovf.default_config_profile, None)

        # Profile list exists
        with VMContextManager(self.input_ovf, None) as ovf:
            # default profile is first in the list
            self.assertEqual(ovf.config_profiles,
                             ["4CPU-4GB-3NIC",
                              "1CPU-1GB-1NIC",
                              "2CPU-2GB-1NIC"])
            self.assertEqual(ovf.default_config_profile, "4CPU-4GB-3NIC")


class TestOVFItem(COT_UT):
    """Unit test cases for the OVFItem class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestOVFItem, self).setUp()
        self.working_dir = tempfile.mkdtemp(prefix="cot_ut_ovfiitem")

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        shutil.rmtree(self.working_dir)
        super(TestOVFItem, self).tearDown()

    def test_1_to_1(self):
        """Convert one Item to an OVFItem and back."""
        root = ET.fromstring("""<?xml version='1.0' encoding='utf-8'?>
<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_ResourceAllocationSettingData" \
xmlns:vmw="http://www.vmware.com/schema/ovf" \
xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_VirtualSystemSettingData">
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
        ovfitem_string = """\
OVFItem:
  Address
    0                    : [None]
  Description
    SCSI Controller      : [None]
  ElementName
    SCSI Controller 0    : [None]
  InstanceID
    3                    : [None]
  ResourceSubType
    lsilogic             : [None]
  ResourceType
    6                    : [None]
"""
        self.assertEqual(str(ovfitem), ovfitem_string)
        self.assertEqual("{0}".format(ovfitem), ovfitem_string)
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
        """Test case for remove_profile() method."""
        with VMContextManager(self.input_ovf, self.temp_file) as ovf:
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
                                            ["2CPU-2GB-1NIC",
                                             "4CPU-4GB-3NIC"]),
                             "11")
            self.assertEqual(item.get_value(ovf.ADDRESS_ON_PARENT,
                                            ["1CPU-1GB-1NIC"]),
                             None)
            self.assertEqual(item.get_value(ovf.ADDRESS_ON_PARENT, [None]),
                             None)
            self.assertEqual(item.get_value(ovf.ADDRESS_ON_PARENT,
                                            ["1CPU-1GB-1NIC",
                                             "2CPU-2GB-1NIC",
                                             "4CPU-4GB-3NIC"]),
                             None)

        self.check_diff("""
       </ovf:Item>
-      <ovf:Item>
+      <ovf:Item ovf:configuration="2CPU-2GB-1NIC 4CPU-4GB-3NIC">
         <rasd:AddressOnParent>11</rasd:AddressOnParent>
""")

    def test_set_property(self):
        """Test cases for set_property() and related methods."""
        ovf = OVF(self.input_ovf, self.temp_file)
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
        ovf.destroy()
