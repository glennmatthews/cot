#!/usr/bin/env python
#
# edit_hardware.py - test cases for the COTEditHardware class
#
# December 2014, Glenn F. Matthews
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

"""Unit test cases for the COT.edit_hardware.COTEditHardware class."""

import re

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.edit_hardware import COTEditHardware
from COT.data_validation import InvalidInputError
from COT.platforms import IOSv, IOSXRv


class TestCOTEditHardware(COT_UT):
    """Test the COTEditHardware class."""

    NEW_HW_FROM_SCRATCH = {
        'levelname': 'WARNING',
        'msg': "No existing items.*Will create new.*from scratch",
    }
    MEMORY_UNIT_GUESS = {
        'levelname': 'WARNING',
        'msg': "Memory units not specified, guessing",
    }
    NO_ITEMS_NO_WORK = {
        'levelname': 'WARNING',
        'msg': "No items.*found. Nothing to do.",
    }
    REMOVING_NETWORK = {
        'levelname': 'WARNING',
        'msg': "Removing unused network.*",
    }

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCOTEditHardware, self).setUp()
        self.instance = COTEditHardware(UI())
        self.instance.output = self.temp_file

    def test_not_ready_with_no_args(self):
        """Test ready_to_run() behavior."""
        self.instance.package = self.input_ovf
        ready, reason = self.instance.ready_to_run()
        self.assertEqual(ready, False)
        self.assertTrue(re.search("No work requested", reason))
        self.assertRaises(InvalidInputError, self.instance.run)

    def test_valid_args(self):
        """Verify that various valid args are accepted and stored."""
        self.instance.package = self.input_ovf
        self.instance.cpus = "1"
        self.assertEqual(self.instance.cpus, 1)
        self.instance.memory = "1GB"
        self.assertEqual(self.instance.memory, 1024)
        self.instance.memory = "2g"
        self.assertEqual(self.instance.memory, 2048)
        self.instance.memory = "256M"
        self.assertEqual(self.instance.memory, 256)
        self.instance.memory = "1024"
        self.assertLogged(**self.MEMORY_UNIT_GUESS)
        self.assertEqual(self.instance.memory, 1024)
        self.instance.nics = 1
        self.assertEqual(self.instance.nics, 1)
        self.instance.serial_ports = 1
        self.assertEqual(self.instance.serial_ports, 1)

    def test_invalid_always_args(self):
        """Verify that various values are always invalid."""
        self.instance.package = self.input_ovf
        with self.assertRaises(InvalidInputError):
            self.instance.cpus = 0
        with self.assertRaises(InvalidInputError):
            self.instance.cpus = "a"
        with self.assertRaises(InvalidInputError):
            self.instance.memory = 0
        with self.assertRaises(InvalidInputError):
            self.instance.memory = "GB"
        with self.assertRaises(InvalidInputError):
            self.instance.nics = -1
        with self.assertRaises(InvalidInputError):
            self.instance.nics = "b"
        with self.assertRaises(InvalidInputError):
            self.instance.serial_ports = -1
        with self.assertRaises(InvalidInputError):
            self.instance.serial_ports = "c"

    def test_valid_by_platform(self):
        """Verify that some input values' validity depends on platform."""
        self.instance.package = self.input_ovf
        # IOSv only supports 1 vCPU and up to 3 GB of RAM
        self.instance.vm._platform = IOSv
        with self.assertRaises(InvalidInputError):
            self.instance.cpus = 2
        with self.assertRaises(InvalidInputError):
            self.instance.memory = "4GB"
        # ...but IOSXRv supports up to 8 CPUs and 3-8 GB of RAM
        self.instance.vm._platform = IOSXRv
        self.instance.cpus = 2
        self.instance.cpus = 8
        with self.assertRaises(InvalidInputError):
            self.instance.cpus = 9
        self.instance.memory = "4"
        self.assertLogged(**self.MEMORY_UNIT_GUESS)
        self.instance.memory = "8GB"
        with self.assertRaises(InvalidInputError):
            self.instance.memory = "9GB"

    def test_set_system_type_single(self):
        """Set the VirtualSystemType to a single value."""
        self.instance.package = self.input_ovf
        self.instance.virtual_system_type = ['vmx-09']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
         <vssd:VirtualSystemIdentifier>test</vssd:VirtualSystemIdentifier>
-        <vssd:VirtualSystemType>vmx-07 vmx-08</vssd:VirtualSystemType>
+        <vssd:VirtualSystemType>vmx-09</vssd:VirtualSystemType>
       </ovf:System>
""")

    def test_set_system_type_list(self):
        """Set the VirtualSystemType to a list of values."""
        self.instance.package = self.input_ovf
        self.instance.virtual_system_type = \
            ['vmx-07', 'vmx-08', 'vmx-09', 'Cisco:Internal:VMCloud-01']
        # 'profiles' will be ignored in this case,
        # as VirtualSystemType is not filtered by profile
        self.instance.profiles = ['2CPU-2GB-1NIC']
        self.instance.run()
        # TODO - catch warning logger message that should be generated
        # due to profiles being ignored.
        self.instance.finished()
        self.check_diff("""
         <vssd:VirtualSystemIdentifier>test</vssd:VirtualSystemIdentifier>
-        <vssd:VirtualSystemType>vmx-07 vmx-08</vssd:VirtualSystemType>
+        <vssd:VirtualSystemType>vmx-07 vmx-08 vmx-09 \
Cisco:Internal:VMCloud-01</vssd:VirtualSystemType>
       </ovf:System>
""")

    def test_set_system_type_no_existing(self):
        """Add a VirtualSystemType to an OVF that doesn't have any."""
        self.instance.package = self.minimal_ovf
        self.instance.virtual_system_type = ['vmx-07', 'vmx-08']
        self.instance.run()
        self.instance.finished()
        self.check_diff(file1=self.minimal_ovf,
                        expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_VirtualSystemSettingData">
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

    def test_set_cpus_one_profile(self):
        """Change the number of CPUs under a specific profile."""
        self.instance.package = self.input_ovf
        self.instance.cpus = 8
        self.instance.profiles = ['2CPU-2GB-1NIC']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
         <rasd:Description>Number of Virtual CPUs</rasd:Description>
-        <rasd:ElementName>2 virtual CPU(s)</rasd:ElementName>
+        <rasd:ElementName>8 virtual CPU(s)</rasd:ElementName>
         <rasd:InstanceID>1</rasd:InstanceID>
         <rasd:ResourceType>3</rasd:ResourceType>
-        <rasd:VirtualQuantity>2</rasd:VirtualQuantity>
+        <rasd:VirtualQuantity>8</rasd:VirtualQuantity>
         <vmw:CoresPerSocket ovf:required="false">1</vmw:CoresPerSocket>
""")

    def test_set_cpus_merge_profiles(self):
        """Change # CPUs under one profile to match another profile."""
        self.instance.package = self.input_ovf
        self.instance.cpus = 4
        self.instance.profiles = ['2CPU-2GB-1NIC']
        self.instance.run()
        self.instance.finished()
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
-      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+      <ovf:Item ovf:configuration="2CPU-2GB-1NIC 4CPU-4GB-3NIC">
         <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
""")

    def test_set_cpus_all_profiles(self):
        """Change value under all profiles, merging a group of Items."""
        self.instance.package = self.input_ovf
        self.instance.cpus = 1
        self.instance.run()
        self.instance.finished()
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
        """Create a CPU definition in an OVF that doesn't have one."""
        self.instance.package = self.minimal_ovf
        self.instance.cpus = 1
        self.instance.run()
        self.assertLogged(**self.NEW_HW_FROM_SCRATCH)
        self.instance.finished()
        self.check_diff(file1=self.minimal_ovf,
                        expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_ResourceAllocationSettingData">
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

    def test_set_memory_one_profile(self):
        """Set memory allocation under one profile."""
        self.instance.package = self.input_ovf
        self.instance.memory = 3072
        self.assertLogged(**self.MEMORY_UNIT_GUESS)
        self.instance.profiles = ['2CPU-2GB-1NIC']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
         <rasd:Description>Memory Size</rasd:Description>
-        <rasd:ElementName>2048MB of memory</rasd:ElementName>
+        <rasd:ElementName>3072MB of memory</rasd:ElementName>
         <rasd:InstanceID>2</rasd:InstanceID>
         <rasd:ResourceType>4</rasd:ResourceType>
-        <rasd:VirtualQuantity>2048</rasd:VirtualQuantity>
+        <rasd:VirtualQuantity>3072</rasd:VirtualQuantity>
       </ovf:Item>
""")

    def test_set_memory_all_profiles(self):
        """Set memory allocation under one profile."""
        self.instance.package = self.input_ovf
        self.instance.memory = "3072M"
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
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
        """Create a RAM definition in an OVF that doesn't have one."""
        self.instance.package = self.minimal_ovf
        self.instance.memory = "4GB"
        self.instance.run()
        self.assertLogged(**self.NEW_HW_FROM_SCRATCH)
        self.instance.finished()
        self.check_diff(file1=self.minimal_ovf,
                        expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_ResourceAllocationSettingData">
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

    def test_set_nic_type_one_profile(self):
        """Set NIC hardware type under a single profile."""
        self.instance.package = self.input_ovf
        self.instance.profiles = ['4CPU-4GB-3NIC']
        self.instance.nic_type = "E1000"
        self.instance.run()
        self.instance.finished()
        # This requires cloning the "default" NIC under instance 11
        # to create a profile-specific version of this NIC
        self.check_diff("""
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:AddressOnParent>11</rasd:AddressOnParent>
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Description>E1000 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:InstanceID>11</rasd:InstanceID>
+        <rasd:ResourceSubType>E1000</rasd:ResourceSubType>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
+      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
         <rasd:AddressOnParent>12</rasd:AddressOnParent>
...
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:Description>E1000 ethernet adapter on "VM Network"\
</rasd:Description>
         <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>E1000</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
...
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:Description>E1000 ethernet adapter on "VM Network"\
</rasd:Description>
         <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>E1000</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
""")

    def test_set_nic_type_all_profiles(self):
        """Change NIC hardware type under all profiles."""
        self.instance.package = self.input_ovf
        self.instance.nic_type = "virtio"
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:Description>VIRTIO ethernet adapter on "VM Network"\
</rasd:Description>
         <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>VIRTIO</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
...
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:Description>VIRTIO ethernet adapter on "VM Network"\
</rasd:Description>
         <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>VIRTIO</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
...
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:Description>VIRTIO ethernet adapter on "VM Network"\
</rasd:Description>
         <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>VIRTIO</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
""")

    def test_set_nic_type_no_existing(self):
        """Set NIC hardware type for an OVF with no NICs (no-op)."""
        self.instance.package = self.minimal_ovf
        self.instance.nic_type = "virtio"
        self.instance.run()
        self.assertLogged(**self.NO_ITEMS_NO_WORK)
        self.instance.finished()
        self.check_diff("", file1=self.minimal_ovf)

    def test_set_nic_count_merge_profiles(self):
        """Add NICs that already exist under one profile to another."""
        self.instance.package = self.input_ovf
        self.instance.nics = 3
        self.instance.profiles = ['2CPU-2GB-1NIC']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
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

    def test_set_nic_count_create_new_one_profile(self):
        """"Create a new NIC under a single profile."""
        self.instance.package = self.input_ovf
        self.instance.nics = '4'
        self.instance.profiles = ['4CPU-4GB-3NIC']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       </ovf:Item>
+      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:AddressOnParent>14</rasd:AddressOnParent>
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:ElementName>Ethernet4</rasd:ElementName>
+        <rasd:InstanceID>14</rasd:InstanceID>
+        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")

    def test_set_nic_count_delete_nics(self):
        """Set NIC count to a lower value, deleting some NICs."""
        self.instance.package = self.input_ovf
        self.instance.nics = 0
        self.instance.profiles = ['1CPU-1GB-1NIC']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       </ovf:Item>
-      <ovf:Item>
+      <ovf:Item ovf:configuration="2CPU-2GB-1NIC 4CPU-4GB-3NIC">
         <rasd:AddressOnParent>11</rasd:AddressOnParent>
""")

    def test_set_nic_network_one_profile(self):
        """Create a new network and map a NIC to it under a single profile."""
        # Create a new network and map to it under one profile
        # This involves splitting the existing NIC into two items
        self.instance.package = self.input_ovf
        self.instance.nic_networks = ['UT']
        self.instance.profiles = ['2CPU-2GB-1NIC']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
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
+        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:InstanceID>11</rasd:InstanceID>
+        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
""")

    def test_set_nic_network_all_profiles(self):
        """Test changing NIC network mapping across all profiles."""
        self.instance.package = self.input_ovf
        self.instance.nic_networks = ['UT', 'UT', 'UT']
        self.instance.run()
        self.instance.finished()
        self.assertLogged(**self.REMOVING_NETWORK)
        self.check_diff("""
     <ovf:Info>The list of logical networks</ovf:Info>
-    <ovf:Network ovf:name="VM Network">
-      <ovf:Description>VM Network</ovf:Description>
+    <ovf:Network ovf:name="UT">
+      <ovf:Description>UT</ovf:Description>
     </ovf:Network>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
""")

    def test_set_nic_network_list_expansion(self):
        """Specify fewer networks than NICs to test implicit NIC assignment.

        Remaining NICs get the last network in the list.
        """
        self.instance.package = self.input_ovf
        self.instance.nic_networks = ['UT1', 'UT2']
        self.instance.run()
        self.instance.finished()
        self.assertLogged(**self.REMOVING_NETWORK)
        self.check_diff("""
     <ovf:Info>The list of logical networks</ovf:Info>
-    <ovf:Network ovf:name="VM Network">
-      <ovf:Description>VM Network</ovf:Description>
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
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT2</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT2</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
""")

    def test_set_nic_network_list_pattern(self):
        """Use wildcard expansion to create multiple networks as needed."""
        self.instance.package = self.input_ovf
        self.instance.nic_networks = ["UT_{20}_network"]
        self.instance.run()
        self.instance.finished()
        self.assertLogged(**self.REMOVING_NETWORK)
        self.check_diff("""
     <ovf:Info>The list of logical networks</ovf:Info>
-    <ovf:Network ovf:name="VM Network">
-      <ovf:Description>VM Network</ovf:Description>
+    <ovf:Network ovf:name="UT_20_network">
+      <ovf:Description>UT_20_network</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="UT_21_network">
+      <ovf:Description>UT_21_network</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="UT_22_network">
+      <ovf:Description>UT_22_network</ovf:Description>
     </ovf:Network>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT_20_network</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT_21_network</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT_22_network</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
""")

    def test_set_nic_mac_address_single_all_profiles(self):
        """Set a single MAC address on all NICs on all profiles."""
        self.instance.package = self.input_ovf
        self.instance.mac_addresses_list = ['10:20:30:40:50:60']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
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

    def test_set_nic_mac_addresses_list_all_profiles(self):
        """Set a sequence of MAC addresses for all profiles."""
        self.instance.package = self.input_ovf
        self.instance.mac_addresses_list = \
            ['10:20:30:40:50:60', '01:02:03:04:05:06', 'ab:cd:ef:00:00:00']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
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

    def test_set_nic_name_list_exact(self):
        """Set a list of names identical in length to the number of NICs."""
        self.instance.package = self.input_ovf
        self.instance.nic_names = ['foo', 'bar', 'baz']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:ElementName>foo</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:ElementName>bar</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:ElementName>baz</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
""")

    def test_set_nic_name_list_extra(self):
        """Set a list of NIC names that's longer than needed."""
        self.instance.package = self.input_ovf
        self.instance.nic_names = ['foo', 'bar', 'baz', 'bat']
        self.instance.run()
        self.assertLogged(levelname="ERROR",
                          msg="not all ElementName values were used")
        self.instance.finished()
        self.check_diff("""
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:ElementName>foo</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:ElementName>bar</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:ElementName>baz</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
""")

    def test_set_nic_name_list_short(self):
        """Set a list of NIC names that's shorter than needed."""
        self.instance.package = self.input_ovf
        self.instance.nic_names = ['foo', 'bar']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:ElementName>foo</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:ElementName>bar</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:ElementName>bar</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
""")

    def test_set_nic_name_pattern(self):
        """Set NIC names based on a pattern."""
        self.instance.package = self.input_ovf
        self.instance.nic_names = ['eth{0}']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:ElementName>eth0</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:ElementName>eth1</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:ElementName>eth2</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
""")

    def test_set_nic_name_list_pattern(self):
        """Set NIC names based on a constant plus a pattern."""
        self.instance.package = self.input_ovf
        self.instance.nic_names = ['foo', 'eth{10}']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:ElementName>foo</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:ElementName>eth10</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
...
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:ElementName>eth11</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
""")

    def test_set_nic_kitchen_sink_all_profiles(self):
        """Test changing many NIC properties at once under all profiles."""
        self.instance.package = self.input_ovf
        self.instance.nic_type = 'e1000'
        self.instance.nic_networks = ['UT1', 'UT2', 'UT3']
        self.instance.mac_addresses_list = \
            ['00:00:00:00:00:01', '11:22:33:44:55:66', 'fe:fd:fc:fb:fa:f9']
        self.instance.run()
        self.instance.finished()
        self.assertLogged(**self.REMOVING_NETWORK)
        self.check_diff("""
     <ovf:Info>The list of logical networks</ovf:Info>
-    <ovf:Network ovf:name="VM Network">
-      <ovf:Description>VM Network</ovf:Description>
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
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:Connection>UT1</rasd:Connection>
+        <rasd:Description>E1000 ethernet adapter on "VM Network"\
</rasd:Description>
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
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:Connection>UT2</rasd:Connection>
+        <rasd:Description>E1000 ethernet adapter on "VM Network"\
</rasd:Description>
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
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:Connection>UT3</rasd:Connection>
+        <rasd:Description>E1000 ethernet adapter on "VM Network"\
</rasd:Description>
         <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>E1000</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
""")

    def test_set_nic_kitchen_sink_one_profile(self):
        """Test changing many NIC properties at once under one profile."""
        self.instance.package = self.input_ovf
        self.instance.profiles = ['4CPU-4GB-3NIC']
        self.instance.nics = 4
        self.instance.nic_networks = ['UT']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
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
+        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
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
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:Connection>UT</rasd:Connection>
         <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
...
         <rasd:InstanceID>13</rasd:InstanceID>
+        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
+      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:AddressOnParent>14</rasd:AddressOnParent>
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Connection>UT</rasd:Connection>
+        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:ElementName>Ethernet4</rasd:ElementName>
+        <rasd:InstanceID>14</rasd:InstanceID>
         <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
""")

    def test_set_nic_kitchen_sink_no_existing(self):
        """Define NIC in an OVF that previously had none."""
        self.instance.package = self.minimal_ovf
        self.instance.nics = 1
        self.instance.nic_networks = ['testme']
        self.instance.mac_addresses_list = ['12:34:56:78:9a:bc']
        self.instance.run()
        self.assertLogged(**self.NEW_HW_FROM_SCRATCH)
        self.instance.finished()
        self.check_diff(file1=self.minimal_ovf,
                        expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_ResourceAllocationSettingData">
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

    def test_set_serial_count_delete_one_profile(self):
        """Remove a shared serial port from one profile only."""
        self.instance.package = self.input_ovf
        self.instance.profiles = ['2CPU-2GB-1NIC']
        self.instance.serial_ports = 1
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       </ovf:Item>
-      <ovf:Item ovf:required="false">
+      <ovf:Item ovf:configuration="1CPU-1GB-1NIC 4CPU-4GB-3NIC" \
ovf:required="false">
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
""")

    def test_set_serial_count_delete_all_profiles(self):
        """Remove a serial port across all profiles."""
        self.instance.package = self.input_ovf
        self.instance.serial_ports = 1
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       </ovf:Item>
-      <ovf:Item ovf:required="false">
-        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Description>Serial Port acting as IOSd Aux Port\
</rasd:Description>
-        <rasd:ElementName>Serial 2</rasd:ElementName>
-        <rasd:InstanceID>10</rasd:InstanceID>
-        <rasd:ResourceType>21</rasd:ResourceType>
-      </ovf:Item>
       <ovf:Item>
""")

    def test_set_serial_count_create_all_profiles(self):
        """Create a serial port under all profiles."""
        self.instance.package = self.input_ovf
        self.instance.serial_ports = 3
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       </ovf:Item>
+      <ovf:Item ovf:required="false">
+        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Description>Serial Port acting as IOSd Aux Port\
</rasd:Description>
+        <rasd:ElementName>Serial 2</rasd:ElementName>
+        <rasd:InstanceID>14</rasd:InstanceID>
+        <rasd:ResourceType>21</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")

    def test_set_serial_count_no_existing(self):
        """Create a serial port in an OVF that had none."""
        self.instance.package = self.minimal_ovf
        self.instance.serial_ports = 1
        self.instance.run()
        self.assertLogged(**self.NEW_HW_FROM_SCRATCH)
        self.instance.finished()
        self.check_diff(file1=self.minimal_ovf,
                        expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_ResourceAllocationSettingData">
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

    def test_set_serial_connectivity_one_port_all_profiles(self):
        """Set serial connectivity for one port under all profiles."""
        self.instance.package = self.input_ovf
        self.instance.serial_connectivity = ['telnet://localhost:22001']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://localhost:22001</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
""")

    def test_set_serial_connectivity_two_ports_all_profiles(self):
        """Set serial connectivity for multiple ports across all profiles."""
        self.instance.package = self.input_ovf
        self.instance.serial_connectivity = \
            ['telnet://localhost:22001', 'telnet://localhost:22002']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://localhost:22001</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
...
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://localhost:22002</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
""")

    def test_serial_create_kitchen_sink(self):
        """Create a serial port and set connectivity in one pass."""
        self.instance.package = self.input_ovf
        self.instance.serial_ports = '3'
        self.instance.serial_connectivity = \
            ['telnet://foo:1', 'telnet://foo:2', 'telnet://foo:3']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
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
+        <rasd:Description>Serial Port acting as IOSd Aux Port\
</rasd:Description>
+        <rasd:ElementName>Serial 2</rasd:ElementName>
+        <rasd:InstanceID>14</rasd:InstanceID>
+        <rasd:ResourceType>21</rasd:ResourceType>
       </ovf:Item>
""")

    def test_serial_delete_kitchen_sink(self):
        """Delete a serial port and set connectivity in one pass."""
        self.instance.package = self.input_ovf
        self.instance.serial_ports = 1
        self.instance.serial_connectivity = ['telnet://bar:22']
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://bar:22</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
...
         <rasd:InstanceID>9</rasd:InstanceID>
-        <rasd:ResourceType>21</rasd:ResourceType>
-      </ovf:Item>
-      <ovf:Item ovf:required="false">
-        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Description>Serial Port acting as IOSd Aux Port\
</rasd:Description>
-        <rasd:ElementName>Serial 2</rasd:ElementName>
-        <rasd:InstanceID>10</rasd:InstanceID>
         <rasd:ResourceType>21</rasd:ResourceType>
""")

    def test_set_scsi_subtype_all_profiles(self):
        """Set SCSI controller subtype under all profiles."""
        self.instance.package = self.input_ovf
        self.instance.scsi_subtype = "virtio"
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
         <rasd:InstanceID>3</rasd:InstanceID>
-        <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
+        <rasd:ResourceSubType>virtio</rasd:ResourceSubType>
         <rasd:ResourceType>6</rasd:ResourceType>
""")

    def test_clear_scsi_subtype_all_profiles(self):
        """Clear SCSI controller subtype under all profiles."""
        self.instance.package = self.input_ovf
        self.instance.scsi_subtype = ""
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
         <rasd:InstanceID>3</rasd:InstanceID>
-        <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
         <rasd:ResourceType>6</rasd:ResourceType>
""")

    def test_set_scsi_subtype_one_profile(self):
        """Set SCSI controller subtype under a single profile."""
        self.instance.package = self.input_ovf
        self.instance.scsi_subtype = "virtio"
        self.instance.profiles = ['4CPU-4GB-3NIC']
        self.instance.run()
        self.instance.finished()
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
        """Set SCSI controller subtype for an OVF with none (no-op)."""
        self.instance.package = self.minimal_ovf
        self.instance.scsi_subtype = "virtio"
        self.instance.run()
        self.assertLogged(**self.NO_ITEMS_NO_WORK)
        self.instance.finished()
        self.check_diff("", file1=self.minimal_ovf)

    def test_set_ide_subtype_all_profiles(self):
        """Set IDE controller subtype across all profiles."""
        self.instance.package = self.input_ovf
        self.instance.ide_subtype = "virtio"
        self.instance.run()
        self.instance.finished()
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

    def test_set_ide_subtype_one_profile(self):
        """Set IDE controller subtype under a single profile."""
        self.instance.package = self.input_ovf
        self.instance.ide_subtype = "virtio"
        self.instance.profiles = ['4CPU-4GB-3NIC']
        self.instance.run()
        self.instance.finished()
        # Here we have to create new controllers under this profile
        # while leaving the default alone
        self.check_diff("""
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
        """Set IDE controller subtype for an OVF with none (no-op)."""
        self.instance.package = self.minimal_ovf
        self.instance.ide_subtype = "virtio"
        self.instance.run()
        self.assertLogged(**self.NO_ITEMS_NO_WORK)
        self.instance.finished()
        self.check_diff("", file1=self.minimal_ovf)

    def test_create_profile_inherit_default(self):
        """Create a new profile that's identical to the default one."""
        self.instance.package = self.input_ovf
        self.instance.profiles = ['UT']
        self.instance.cpus = 1
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
     </ovf:Configuration>
+    <ovf:Configuration ovf:id="UT">
+      <ovf:Label>UT</ovf:Label>
+      <ovf:Description>UT</ovf:Description>
+    </ovf:Configuration>
   </ovf:DeploymentOptionSection>
""")

    def test_create_new_profile(self):
        """Create a new profile with new values."""
        self.instance.package = self.input_ovf
        self.instance.profiles = ['UT']
        self.instance.cpus = 8
        self.instance.run()
        self.instance.finished()
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

    def test_create_two_profiles(self):
        """Create two profiles at once."""
        self.instance.package = self.input_ovf
        self.instance.profiles = ['UT', 'UT2']
        self.instance.memory = 8192
        self.assertLogged(**self.MEMORY_UNIT_GUESS)
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
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
        """Add a profile to an OVF that doesn't have any."""
        self.instance.package = self.minimal_ovf
        self.instance.profiles = ['UT']
        self.instance.run()
        self.instance.finished()
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
   <ovf:VirtualSystem ovf:id="x">
""")

    def test_delete_one_profile(self):
        """Delete one configuration profile."""
        self.instance.package = self.input_ovf
        self.instance.profiles = ['1CPU-1GB-1NIC', '4CPU-4GB-3NIC']
        self.instance.delete_all_other_profiles = True
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
     </ovf:Configuration>
-    <ovf:Configuration ovf:id="2CPU-2GB-1NIC">
-      <ovf:Label>2 vCPUs, 2 GB RAM, 1 NIC</ovf:Label>
-      <ovf:Description>Minimal hardware profile - 2 vCPUs, 2 GB RAM, \
1 NIC</ovf:Description>
-    </ovf:Configuration>
     <ovf:Configuration ovf:default="true" ovf:id="4CPU-4GB-3NIC">
...
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
...
         <rasd:VirtualQuantity>1024</rasd:VirtualQuantity>
-      </ovf:Item>
-      <ovf:Item ovf:configuration="2CPU-2GB-1NIC">
-        <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
-        <rasd:Description>Memory Size</rasd:Description>
-        <rasd:ElementName>2048MB of memory</rasd:ElementName>
-        <rasd:InstanceID>2</rasd:InstanceID>
-        <rasd:ResourceType>4</rasd:ResourceType>
-        <rasd:VirtualQuantity>2048</rasd:VirtualQuantity>
       </ovf:Item>
""")

    def test_delete_all_profiles(self):
        """Delete all configuration profiles, leaving only the default hw."""
        self.instance.package = self.input_ovf
        self.instance.delete_all_other_profiles = True
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
   </ovf:NetworkSection>
-  <ovf:DeploymentOptionSection>
-    <ovf:Info>Configuration Profiles</ovf:Info>
-    <ovf:Configuration ovf:id="1CPU-1GB-1NIC">
-      <ovf:Label>1 vCPU, 1 GB RAM, 1 NIC</ovf:Label>
-      <ovf:Description>Minimal hardware profile - 1 vCPU, 1 GB RAM, 1 NIC\
</ovf:Description>
-    </ovf:Configuration>
-    <ovf:Configuration ovf:id="2CPU-2GB-1NIC">
-      <ovf:Label>2 vCPUs, 2 GB RAM, 1 NIC</ovf:Label>
-      <ovf:Description>Minimal hardware profile - 2 vCPUs, 2 GB RAM, 1 NIC\
</ovf:Description>
-    </ovf:Configuration>
-    <ovf:Configuration ovf:default="true" ovf:id="4CPU-4GB-3NIC">
-      <ovf:Label>4 vCPUs, 4 GB RAM, 3 NICs</ovf:Label>
-      <ovf:Description>Default hardware profile - 4 vCPUs, 4 GB RAM, 3 NICs\
</ovf:Description>
-    </ovf:Configuration>
-  </ovf:DeploymentOptionSection>
   <ovf:VirtualSystem ovf:id="test">
...
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
...
         <rasd:VirtualQuantity>1024</rasd:VirtualQuantity>
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
       </ovf:Item>
...
       </ovf:Item>
-      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
-        <rasd:AddressOnParent>12</rasd:AddressOnParent>
-        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
-        <rasd:InstanceID>12</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
-        <rasd:ResourceType>10</rasd:ResourceType>
-      </ovf:Item>
-      <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
-        <rasd:AddressOnParent>13</rasd:AddressOnParent>
-        <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
-        <rasd:InstanceID>13</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
-        <rasd:ResourceType>10</rasd:ResourceType>
-      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")

    def test_create_delete_network_no_existing(self):
        """Create then delete a network in an OVF with none previously."""
        self.instance.package = self.minimal_ovf
        self.instance.nic_networks = ["VM Network", "Foobar"]
        self.instance.nics = 1
        self.instance.run()
        self.assertLogged(**self.NEW_HW_FROM_SCRATCH)
        self.assertLogged(levelname="ERROR",
                          msg="not all Connection values were used")
        self.instance.finished()
        # network 'Foobar' is not used, so it'll be deleted
        self.assertLogged(**self.REMOVING_NETWORK)
        self.check_diff(file1=self.minimal_ovf,
                        expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_ResourceAllocationSettingData">
   <ovf:References />
+  <ovf:NetworkSection>
+    <ovf:Info>Logical networks</ovf:Info>
+    <ovf:Network ovf:name="VM Network">
+      <ovf:Description>VM Network</ovf:Description>
+    </ovf:Network>
+  </ovf:NetworkSection>
   <ovf:VirtualSystem ovf:id="x">
...
       <ovf:Info />
+      <ovf:Item>
+        <rasd:Connection>VM Network</rasd:Connection>
+        <rasd:ElementName>Ethernet1</rasd:ElementName>
+        <rasd:InstanceID>1</rasd:InstanceID>
+        <rasd:ResourceType>10</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")
        self.instance.destroy()
        self.instance = None
        self.validate_with_ovftool(self.temp_file)

        # Now remove all NICs and make sure it's cleaned back up
        self.instance = COTEditHardware(UI())
        self.instance.output = self.temp_file
        self.instance.package = self.temp_file
        self.instance.nics = 0
        self.instance.run()
        self.instance.finished()
        self.assertLogged(**self.REMOVING_NETWORK)
        self.assertLogged(levelname="WARNING",
                          msg="removing NetworkSection")
        self.check_diff(file1=self.temp_file, file2=self.minimal_ovf,
                        expected="")
