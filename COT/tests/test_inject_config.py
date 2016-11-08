#!/usr/bin/env python
#
# test_inject_config.py - test cases for the COTInjectConfig class
#
# December 2014, Glenn F. Matthews
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

"""Unit test cases for the COT.inject_config.COTInjectConfig class."""

import logging
import os.path
import re
import shutil
import tempfile

import mock
from pkg_resources import resource_filename

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.inject_config import COTInjectConfig
from COT.data_validation import InvalidInputError, ValueUnsupportedError
from COT.platforms import CSR1000V, IOSv, IOSXRv, IOSXRvLC
from COT.helpers import helpers
from COT.disks import disk_representation_from_file
from COT.remove_file import COTRemoveFile

logger = logging.getLogger(__name__)


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
        # IOSXRv is the only platform that supports both primary and secondary
        # config, so fake out our platform type appropriately.
        self.set_vm_platform(IOSXRv)

        ready, reason = self.instance.ready_to_run()
        self.assertFalse(ready)
        self.assertTrue(re.search("No files specified", reason))
        self.assertRaises(InvalidInputError, self.instance.run)

        self.instance.config_file = self.config_file
        ready, reason = self.instance.ready_to_run()
        self.assertTrue(ready)

        self.instance.config_file = None
        ready, reason = self.instance.ready_to_run()
        self.assertFalse(ready)

        self.instance.secondary_config_file = self.config_file
        ready, reason = self.instance.ready_to_run()
        self.assertTrue(ready)

        self.instance.secondary_config_file = None
        ready, reason = self.instance.ready_to_run()
        self.assertFalse(ready)

        self.instance.extra_files = [self.config_file]
        ready, reason = self.instance.ready_to_run()
        self.assertTrue(ready)

    def test_invalid_always_args(self):
        """Test input values that are always invalid."""
        self.instance.package = self.input_ovf
        with self.assertRaises(InvalidInputError):
            self.instance.config_file = 0
        with self.assertRaises(InvalidInputError):
            self.instance.secondary_config_file = 0
        with self.assertRaises(InvalidInputError):
            self.instance.extra_files = [self.input_ovf, '/foo/bar']

    def test_valid_by_platform(self):
        """Test input values whose validity depends on the platform."""
        self.instance.package = self.input_ovf
        # IOSXRvLC supports neither primary nor secondary config files
        self.set_vm_platform(IOSXRvLC)
        with self.assertRaises(InvalidInputError):
            self.instance.config_file = self.config_file
        with self.assertRaises(InvalidInputError):
            self.instance.secondary_config_file = self.config_file
        # IOSv supports primary but not secondary
        self.set_vm_platform(IOSv)
        self.instance.config_file = self.config_file
        with self.assertRaises(InvalidInputError):
            self.instance.secondary_config_file = self.config_file
        # IOSXRv supports both
        self.set_vm_platform(IOSXRv)
        self.instance.config_file = self.config_file
        self.instance.secondary_config_file = self.config_file

    def test_inject_config_iso(self):
        """Inject config file on an ISO."""
        self.instance.package = self.input_ovf
        self.instance.config_file = self.config_file
        self.instance.run()
        self.assertLogged(**self.OVERWRITING_DISK_ITEM)
        self.instance.finished()
        config_iso = os.path.join(self.temp_dir, 'config.iso')
        self.check_diff("""
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
+    <ovf:File ovf:href="config.iso" ovf:id="config.iso" \
ovf:size="{config_size}" />
   </ovf:References>
...
         <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>CD-ROM 2</rasd:ElementName>
+        <rasd:HostResource>ovf:/file/config.iso</rasd:HostResource>
         <rasd:InstanceID>8</rasd:InstanceID>"""
                        .format(cfg_size=self.FILE_SIZE['sample_cfg.txt'],
                                config_size=os.path.getsize(config_iso)))
        if helpers['isoinfo']:
            # The sample_cfg.text should be renamed to the platform-specific
            # file name for bootstrap config - in this case, config.txt
            self.assertEqual(disk_representation_from_file(config_iso).files,
                             ["config.txt"])
        else:
            logger.info("isoinfo not available, not checking disk contents")

    def test_inject_config_iso_secondary(self):
        """Inject secondary config file on an ISO."""
        self.instance.package = self.input_ovf
        self.set_vm_platform(IOSXRv)
        self.instance.secondary_config_file = self.config_file
        self.instance.run()
        self.assertLogged(**self.OVERWRITING_DISK_ITEM)
        self.instance.finished()
        self.assertLogged(**self.invalid_hardware_warning(
            '4CPU-4GB-3NIC', 'VMXNET3', 'NIC type'))
        self.assertLogged(**self.invalid_hardware_warning(
            '1CPU-1GB-1NIC', 'VMXNET3', 'NIC type'))
        self.assertLogged(**self.invalid_hardware_warning(
            '1CPU-1GB-1NIC', '1024 MiB', 'RAM'))
        self.assertLogged(**self.invalid_hardware_warning(
            '2CPU-2GB-1NIC', 'VMXNET3', 'NIC type'))
        self.assertLogged(**self.invalid_hardware_warning(
            '2CPU-2GB-1NIC', '2048 MiB', 'RAM'))
        config_iso = os.path.join(self.temp_dir, 'config.iso')
        self.check_diff("""
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
+    <ovf:File ovf:href="config.iso" ovf:id="config.iso" \
ovf:size="{config_size}" />
   </ovf:References>
...
         <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>CD-ROM 2</rasd:ElementName>
+        <rasd:HostResource>ovf:/file/config.iso</rasd:HostResource>
         <rasd:InstanceID>8</rasd:InstanceID>"""
                        .format(cfg_size=self.FILE_SIZE['sample_cfg.txt'],
                                config_size=os.path.getsize(config_iso)))
        if helpers['isoinfo']:
            # The sample_cfg.text should be renamed to the platform-specific
            # file name for secondary bootstrap config
            self.assertEqual(disk_representation_from_file(config_iso).files,
                             ["iosxr_config_admin.txt"])
        else:
            logger.info("isoinfo not available, not checking disk contents")

    def test_inject_config_iso_multiple_drives(self):
        """Inject config file on an ISO when multiple empty drives exist."""
        temp_ovf = os.path.join(self.temp_dir, "intermediate.ovf")

        # Remove the existing ISO from our input_ovf:
        rm = COTRemoveFile(UI())
        rm.package = self.input_ovf
        rm.output = temp_ovf
        rm.file_path = "input.iso"
        rm.run()
        rm.finished()
        rm.destroy()

        # Now we have two empty drives.
        self.instance.package = temp_ovf
        self.instance.config_file = self.config_file
        self.instance.run()
        self.assertLogged(**self.OVERWRITING_DISK_ITEM)
        self.instance.finished()
        config_iso = os.path.join(self.temp_dir, 'config.iso')
        self.check_diff("""
     <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{vmdk_size}" />
-    <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
+    <ovf:File ovf:href="config.iso" ovf:id="config.iso" \
ovf:size="{config_size}" />
   </ovf:References>
...
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>CD-ROM 1</rasd:ElementName>
-        <rasd:HostResource>ovf:/file/file2</rasd:HostResource>
+        <rasd:HostResource>ovf:/file/config.iso</rasd:HostResource>
         <rasd:InstanceID>7</rasd:InstanceID>"""
                        .format(vmdk_size=self.FILE_SIZE['input.vmdk'],
                                iso_size=self.FILE_SIZE['input.iso'],
                                cfg_size=self.FILE_SIZE['sample_cfg.txt'],
                                config_size=os.path.getsize(config_iso)))
        if helpers['isoinfo']:
            # The sample_cfg.text should be renamed to the platform-specific
            # file name for bootstrap config - in this case, config.txt
            self.assertEqual(disk_representation_from_file(config_iso).files,
                             ["config.txt"])
        else:
            logger.info("isoinfo not available, not checking disk contents")

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
        config_vmdk = os.path.join(self.temp_dir, 'config.vmdk')
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
                                config_size=os.path.getsize(config_vmdk)))
        # TODO - we don't currently have a way to check VMDK file listing
        # self.assertEqual(disk_representation_from_file(config_vmdk).files,
        #                 ["ios_config.txt"])

    def test_inject_config_unsupported_format_existing(self):
        """Only 'harddisk' and 'cdrom' config drives are supported."""
        self.instance.package = self.input_ovf
        self.instance.config_file = self.config_file
        # Failure during initial lookup of existing drive
        # pylint: disable=protected-access
        with mock.patch.object(self.instance.vm._platform,
                               'BOOTSTRAP_DISK_TYPE',
                               new_callable=mock.PropertyMock,
                               return_value='floppy'):
            self.assertRaises(ValueUnsupportedError, self.instance.run)

    def test_inject_config_unsupported_format_new_disk(self):
        """Only 'harddisk' and 'cdrom' config drives are supported."""
        self.instance.package = self.input_ovf
        self.instance.config_file = self.config_file
        # Drive lookup passes, but failure to create new disk
        # pylint: disable=protected-access
        with mock.patch.object(self.instance.vm._platform,
                               'BOOTSTRAP_DISK_TYPE',
                               new_callable=mock.PropertyMock,
                               side_effect=('cdrom', 'cdrom',
                                            'floppy', 'floppy', 'floppy')):
            self.assertRaises(ValueUnsupportedError, self.instance.run)

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
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
+    <ovf:File ovf:href="config.iso" ovf:id="config.iso" \
ovf:size="{config_size}" />
   </ovf:References>
...
         <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>CD-ROM 2</rasd:ElementName>
+        <rasd:HostResource>ovf:/file/config.iso</rasd:HostResource>
         <rasd:InstanceID>8</rasd:InstanceID>"""
                        .format(cfg_size=self.FILE_SIZE['sample_cfg.txt'],
                                config_size=os.path.getsize(os.path.join(
                                    self.temp_dir, 'config.iso'))))

    def test_inject_config_fail_no_disk_available(self):
        """Error handling if the OVF doesn't have an appropriate drive."""
        self.instance.package = self.minimal_ovf
        self.instance.config_file = self.config_file
        # CSR1000V wants a CD-ROM drive
        self.set_vm_platform(CSR1000V)
        self.assertRaises(LookupError, self.instance.run)
        # IOSv wants a hard disk - will fail due to no DiskSection
        self.set_vm_platform(IOSv)
        self.assertRaises(LookupError, self.instance.run)

        # Also fail due to DiskSection but no placeholder:
        self.instance.package = self.input_ovf
        self.set_vm_platform(IOSv)
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

    def test_inject_extra_directory(self):
        """Test injection of extras from an entire directory."""
        self.instance.package = self.input_ovf
        extra_dir = tempfile.mkdtemp(prefix="cot_ic_ut")
        try:
            shutil.copy(self.input_ovf, extra_dir)
            shutil.copy(self.minimal_ovf, extra_dir)
            subdir = os.path.join(extra_dir, "subdirectory")
            os.makedirs(subdir)
            shutil.copy(self.invalid_ovf, subdir)

            self.instance.extra_files = [extra_dir]
            self.instance.run()
            self.assertLogged(**self.OVERWRITING_DISK_ITEM)
            self.instance.finished()

            config_iso = os.path.join(self.temp_dir, 'config.iso')
            if helpers['isoinfo']:
                self.assertEqual(
                    disk_representation_from_file(config_iso).files,
                    [
                        'input.ovf',
                        'minimal.ovf',
                        'subdirectory',
                        'subdirectory/invalid.ovf',
                    ]
                )
            else:
                logger.info("isoinfo not present, not checking disk contents")
        finally:
            shutil.rmtree(extra_dir)

    def test_inject_config_primary_secondary_extra(self):
        """Test injection of primary and secondary files and extras."""
        self.instance.package = self.input_ovf
        # IOSXRv supports secondary config
        self.set_vm_platform(IOSXRv)
        self.instance.config_file = self.config_file
        self.instance.secondary_config_file = self.config_file
        self.instance.extra_files = [self.minimal_ovf, self.vmware_ovf]
        self.instance.run()
        self.assertLogged(**self.OVERWRITING_DISK_ITEM)
        self.instance.finished()
        self.assertLogged(**self.invalid_hardware_warning(
            '4CPU-4GB-3NIC', 'VMXNET3', 'NIC type'))
        self.assertLogged(**self.invalid_hardware_warning(
            '1CPU-1GB-1NIC', 'VMXNET3', 'NIC type'))
        self.assertLogged(**self.invalid_hardware_warning(
            '1CPU-1GB-1NIC', '1024 MiB', 'RAM'))
        self.assertLogged(**self.invalid_hardware_warning(
            '2CPU-2GB-1NIC', 'VMXNET3', 'NIC type'))
        self.assertLogged(**self.invalid_hardware_warning(
            '2CPU-2GB-1NIC', '2048 MiB', 'RAM'))
        config_iso = os.path.join(self.temp_dir, 'config.iso')
        self.check_diff("""
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
+    <ovf:File ovf:href="config.iso" ovf:id="config.iso" \
ovf:size="{config_size}" />
   </ovf:References>
...
         <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
+        <rasd:Description>Configuration disk</rasd:Description>
         <rasd:ElementName>CD-ROM 2</rasd:ElementName>
+        <rasd:HostResource>ovf:/file/config.iso</rasd:HostResource>
         <rasd:InstanceID>8</rasd:InstanceID>"""
                        .format(cfg_size=self.FILE_SIZE['sample_cfg.txt'],
                                config_size=os.path.getsize(config_iso)))
        if helpers['isoinfo']:
            self.assertEqual(
                disk_representation_from_file(config_iso).files,
                [
                    "iosxr_config.txt",
                    "iosxr_config_admin.txt",
                    "minimal.ovf",
                    "vmware.ovf",
                ]
            )
        else:
            logger.info("isoinfo not available, not checking disk contents")
