#!/usr/bin/env python
#
# test_item.py - Unit test cases for OVFItem class
#
# June 2016, Glenn F. Matthews
# Copyright (c) 2013-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for COT.ovf.OVFItem class."""

import tempfile
import shutil
import xml.etree.ElementTree as ET

from COT.tests.ut import COT_UT

from COT.ovf import OVF
from COT.ovf.name_helper import OVFNameHelper1
from COT.ovf.item import OVFItem
from COT.vm_context_manager import VMContextManager


class TestOVFItem(COT_UT):
    """Unit test cases for the OVFItem class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestOVFItem, self).setUp()
        self.maxDiff = None
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
        helper = OVFNameHelper1()
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
    ('lsilogic',)        : [None]
  ResourceType
    6                    : [None]
"""
        self.assertEqual(ovfitem_string, str(ovfitem))
        self.assertEqual(ovfitem_string, "{0}".format(ovfitem))
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
        self.assertFalse(item.modified)

        # Set profile 1 to same as default (this is a no-op)
        item.set_property(ovf.VIRTUAL_QUANTITY, '1', ["1CPU-1GB-1NIC"])
        self.assertFalse(item.modified)
        ovf.write()
        self.check_diff("")

        # Change profile 1 to same as profile 2
        item.set_property(ovf.VIRTUAL_QUANTITY, '2', ["1CPU-1GB-1NIC"])
        self.assertEqual(item.get_value(ovf.VIRTUAL_QUANTITY,
                                        ['1CPU-1GB-1NIC', '2CPU-2GB-1NIC']),
                         '2')
        self.assertTrue(item.modified)
        ovf.write()
        self.check_diff("""
       </ovf:Item>
-      <ovf:Item ovf:configuration="2CPU-2GB-1NIC">
+      <ovf:Item ovf:configuration="1CPU-1GB-1NIC 2CPU-2GB-1NIC">
         <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
""")

        # Change profile 1 back under default
        item.set_property(ovf.VIRTUAL_QUANTITY, '1', ["1CPU-1GB-1NIC"])
        self.assertTrue(item.modified)
        ovf.write()
        self.check_diff("")

        # Change profile 2 to fall under default
        item.set_property(ovf.VIRTUAL_QUANTITY, '1', ["2CPU-2GB-1NIC"])
        self.assertTrue(item.modified)
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

    def test_set_property_no_modification(self):
        """Test various operations that should do nothing."""
        ovf = OVF(self.input_ovf, self.temp_file)
        hw = ovf.hardware
        # InstanceID 4, IDE controller
        item = hw.item_dict['4']

        # set global value to empty for a property with no value
        self.assertFalse(item.modified)
        item.set_property(ovf.RESOURCE_SUB_TYPE, '')
        self.assertFalse(item.modified)

        # set per-profile value to empty for a property with no value
        item.set_property(ovf.RESOURCE_SUB_TYPE, '', ['2CPU-2GB-1NIC'])
        self.assertFalse(item.modified)

        # set global value to the same as existing global value
        item.set_property(ovf.ELEMENT_NAME, "VirtualIDEController 1")
        self.assertFalse(item.modified)

        # set per-profile value to the same as existing global value
        item.set_property(ovf.ELEMENT_NAME, "VirtualIDEController 1",
                          ['2CPU-2GB-1NIC'])
        self.assertFalse(item.modified)

        ovf.write()
        ovf.destroy()
        self.check_diff("")
