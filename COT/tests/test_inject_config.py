#!/usr/bin/env python
#
# inject_config.py - test cases for the COTInjectConfig class
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

"""Unit test cases for the COT.inject_config.COTInjectConfig class."""

import os.path
import re
from pkg_resources import resource_filename

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.inject_config import COTInjectConfig
from COT.data_validation import InvalidInputError
from COT.platforms import CSR1000V, IOSv, IOSXRv, IOSXRvLC


class TestCOTInjectConfig(COT_UT):
    """Test cases for COTInjectConfig class."""

    # Expected WARNING message
    OVERWRITE_CONFIG_DISK = {
        'levelname': 'WARNING',
        'msg': "Overwriting existing config disk",
    }

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCOTInjectConfig, self).setUp()
        self.instance = COTInjectConfig(UI())
        self.instance.output = self.temp_file
        self.config_file = resource_filename(__name__, "sample_cfg.txt")

    def test_readiness(self):
        """Test ready_to_run() under various combinations of parameters."""
        self.instance.package = self.input_ovf
        ready, reason = self.instance.ready_to_run()
        self.assertFalse(ready)
        self.assertTrue(re.search("No configuration files", reason))
        self.assertRaises(InvalidInputError, self.instance.run)

        self.instance.config_file = self.config_file
        ready, reason = self.instance.ready_to_run()
        self.assertTrue(ready)

    def test_invalid_always_args(self):
        """Test input values that are always invalid."""
        self.instance.package = self.input_ovf
        with self.assertRaises(InvalidInputError):
            self.instance.config_file = 0
        with self.assertRaises(InvalidInputError):
            self.instance.secondary_config_file = 0

    def test_valid_by_platform(self):
        """Test input values whose validity depends on the platform."""
        self.instance.package = self.input_ovf
        # IOSXRvLC supports neither primary nor secondary config files
        self.instance.vm._platform = IOSXRvLC
        with self.assertRaises(InvalidInputError):
            self.instance.config_file = self.config_file
        with self.assertRaises(InvalidInputError):
            self.instance.secondary_config_file = self.config_file
        # IOSv supports primary but not secondary
        self.instance.vm._platform = IOSv
        self.instance.config_file = self.config_file
        with self.assertRaises(InvalidInputError):
            self.instance.secondary_config_file = self.config_file
        # IOSXRv supports both
        self.instance.vm._platform = IOSXRv
        self.instance.config_file = self.config_file
        self.instance.secondary_config_file = self.config_file

    def test_inject_config_iso(self):
        """Inject config file on an ISO."""
        self.instance.package = self.input_ovf
        self.instance.config_file = self.config_file
        self.instance.run()
        self.assertLogged(**self.OVERWRITING_DISK_ITEM)
        self.instance.finished()
        self.check_diff("""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="config.iso" ovf:id="config.iso" \
ovf:size="{config_size}" />
   </ovf:References>
...
         <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>CD-ROM 2</rasd:ElementName>
+        <rasd:HostResource>ovf:/file/config.iso</rasd:HostResource>
         <rasd:InstanceID>8</rasd:InstanceID>"""
                        .format(iso_size=self.FILE_SIZE['input.iso'],
                                config_size=os.path.getsize(os.path.join(
                                    self.temp_dir, 'config.iso'))))

    def test_inject_config_iso_secondary(self):
        """Inject secondary config file on an ISO."""
        self.instance.package = self.input_ovf
        self.instance.vm._platform = IOSXRv
        self.instance.secondary_config_file = self.config_file
        self.instance.run()
        self.assertLogged(**self.OVERWRITING_DISK_ITEM)
        self.instance.finished()
        self.check_diff("""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="config.iso" ovf:id="config.iso" \
ovf:size="{config_size}" />
   </ovf:References>
...
         <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>CD-ROM 2</rasd:ElementName>
+        <rasd:HostResource>ovf:/file/config.iso</rasd:HostResource>
         <rasd:InstanceID>8</rasd:InstanceID>"""
                        .format(iso_size=self.FILE_SIZE['input.iso'],
                                config_size=os.path.getsize(os.path.join(
                                    self.temp_dir, 'config.iso'))))

    def test_inject_config_vmdk(self):
        """Inject config file on a VMDK."""
        self.instance.package = self.iosv_ovf
        self.instance.config_file = self.config_file
        self.instance.run()
        self.assertLogged(**self.OVERWRITING_DISK)
        self.assertLogged(**self.OVERWRITING_DISK_ITEM)
        self.instance.finished()
        # Note that in this case there is an existing placeholder Disk;
        # to be OVF standard compliant, the new File must be created in the
        # same order relative to the other Files as the existing Disk is
        # to the other Disks.
        self.check_diff(file1=self.iosv_ovf,
                        expected="""
   <ovf:References>
+    <ovf:File ovf:href="config.vmdk" ovf:id="config.vmdk" \
ovf:size="{config_size}" />
     <ovf:File ovf:href="input.vmdk" ovf:id="vios-adventerprisek9-m.vmdk" \
ovf:size="{input_size}" />
...
     <ovf:Info>Virtual disk information</ovf:Info>
-    <ovf:Disk ovf:capacity="128" ovf:capacityAllocationUnits="byte * 2^20" \
ovf:diskId="flash2" ovf:format=\
"http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
+    <ovf:Disk ovf:capacity="8" ovf:capacityAllocationUnits="byte * 2^20" \
ovf:diskId="flash2" ovf:fileRef="config.vmdk" ovf:format=\
"http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
     <ovf:Disk ovf:capacity="1073741824" ovf:capacityAllocationUnits="byte" \
ovf:diskId="vios-adventerprisek9-m.vmdk" \
ovf:fileRef="vios-adventerprisek9-m.vmdk" ovf:format=\
"http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />
...
         <rasd:AddressOnParent>1</rasd:AddressOnParent>
-        <rasd:Description>Disk device corresponding to flash2:; may be used \
for bootstrap configuration.</rasd:Description>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>flash2</rasd:ElementName>"""
                        .format(input_size=self.FILE_SIZE['input.vmdk'],
                                config_size=os.path.getsize(os.path.join(
                                    self.temp_dir, 'config.vmdk'))))

    def test_inject_config_repeatedly(self):
        """inject-config repeatedly."""
        # Add initial config file
        self.instance.package = self.input_ovf
        self.instance.config_file = self.config_file
        self.instance.run()
        self.assertLogged(**self.OVERWRITING_DISK_ITEM)
        self.instance.finished()
        # Overwrite it with a new one
        self.instance.package = self.temp_file
        self.instance.config_file = self.config_file
        self.instance.run()
        self.assertLogged(**self.OVERWRITE_CONFIG_DISK)
        self.assertLogged(**self.OVERWRITING_FILE)
        self.assertLogged(**self.OVERWRITING_DISK_ITEM)
        self.instance.finished()
        # And again.
        self.instance.package = self.temp_file
        self.instance.config_file = self.config_file
        self.instance.run()
        self.assertLogged(**self.OVERWRITE_CONFIG_DISK)
        self.assertLogged(**self.OVERWRITING_FILE)
        self.assertLogged(**self.OVERWRITING_DISK_ITEM)
        self.instance.finished()
        self.check_diff("""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
+    <ovf:File ovf:href="config.iso" ovf:id="config.iso" \
ovf:size="{config_size}" />
   </ovf:References>
...
         <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>CD-ROM 2</rasd:ElementName>
+        <rasd:HostResource>ovf:/file/config.iso</rasd:HostResource>
         <rasd:InstanceID>8</rasd:InstanceID>"""
                        .format(iso_size=self.FILE_SIZE['input.iso'],
                                config_size=os.path.getsize(os.path.join(
                                    self.temp_dir, 'config.iso'))))

    def test_inject_config_fail_no_disk_available(self):
        """Error handling if the OVF doesn't have an appropriate drive."""
        self.instance.package = self.minimal_ovf
        self.instance.config_file = self.config_file
        # CSR1000V wants a CD-ROM drive
        self.instance.vm._platform = CSR1000V
        self.assertRaises(LookupError, self.instance.run)
        # IOSv wants a hard disk - will fail due to no DiskSection
        self.instance.vm._platform = IOSv
        self.assertRaises(LookupError, self.instance.run)

        # Also fail due to DiskSection but no placeholder:
        self.instance.package = self.input_ovf
        self.instance.vm._platform = IOSv
        self.assertRaises(LookupError, self.instance.run)

    def test_find_parent_fail_no_parent(self):
        """Negative testing of some inject-config related APIs."""
        self.instance.package = self.input_ovf
        cpu_item = self.instance.vm.hardware.find_item(
            resource_type='cpu')
        self.assertRaises(LookupError,
                          self.instance.vm.find_device_location, cpu_item)
        self.assertLogged(levelname="ERROR",
                          msg="Item has no .*Parent element")
