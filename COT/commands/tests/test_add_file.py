#!/usr/bin/env python
#
# test_add_file.py - test cases for the COTAddFile class
#
# January 2015, Glenn F. Matthews
# Copyright (c) 2013-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for COT.add_file.COTAddFile class."""

import os.path

from COT.commands.tests.command_testcase import CommandTestCase
from COT.ui import UI
from COT.commands.add_file import COTAddFile
from COT.data_validation import InvalidInputError


class TestCOTAddFile(CommandTestCase):
    """Test cases for the COTAddFile module."""

    command_class = COTAddFile

    def test_readiness(self):
        """Test ready_to_run() under various combinations of parameters."""
        ready, reason = self.command.ready_to_run()
        self.assertFalse(ready)
        self.assertEqual("FILE is a mandatory argument!", reason)
        self.assertRaises(InvalidInputError, self.command.run)

        self.command.file = self.iosv_ovf
        ready, reason = self.command.ready_to_run()
        self.assertFalse(ready)
        self.assertEqual("PACKAGE is a mandatory argument!", reason)
        self.assertRaises(InvalidInputError, self.command.run)

        self.command.package = self.input_ovf
        ready, reason = self.command.ready_to_run()
        self.assertTrue(ready)

    def test_add_file(self):
        """Basic file addition."""
        self.command.package = self.input_ovf
        self.command.file = self.iosv_ovf
        self.command.run()
        self.command.finished()
        self.check_diff("""
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
+    <ovf:File ovf:href="iosv.ovf" ovf:id="iosv.ovf" ovf:size="{ovf_size}" />
   </ovf:References>
""".format(cfg_size=self.FILE_SIZE['sample_cfg.txt'],
           ovf_size=os.path.getsize(self.iosv_ovf)))

    def test_add_file_with_id(self):
        """Add a file with explicit 'file_id' argument."""
        self.command.package = self.input_ovf
        self.command.file = self.iosv_ovf
        self.command.file_id = "myfile"
        self.command.run()
        self.command.finished()
        self.check_diff("""
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
+    <ovf:File ovf:href="iosv.ovf" ovf:id="myfile" ovf:size="{ovf_size}" />
   </ovf:References>
""".format(cfg_size=self.FILE_SIZE['sample_cfg.txt'],
           ovf_size=os.path.getsize(self.iosv_ovf)))

    def test_overwrite_file(self):
        """Overwrite a file implicitly."""
        self.command.package = self.input_ovf
        self.command.file = self.input_iso
        self.command.run()
        self.assertLogged(**self.OVERWRITING_FILE)
        self.command.finished()
        self.check_diff("")

    def test_add_file_then_change_to_disk(self):
        """Add a disk as a file, then make it a proper disk."""
        self.command.package = self.minimal_ovf
        intermediate_ovf = os.path.join(self.temp_dir, "mid.ovf")
        self.command.output = intermediate_ovf
        self.command.file = self.blank_vmdk
        self.command.file_id = "mydisk"
        self.command.run()
        self.command.finished()
        self.check_diff(file1=self.minimal_ovf,
                        file2=intermediate_ovf,
                        expected="""
 <ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
-  <ovf:References />
+  <ovf:References>
+    <ovf:File ovf:href="blank.vmdk" ovf:id="mydisk" ovf:size="{0}" />
+  </ovf:References>
   <ovf:VirtualSystem ovf:id="x">
""".format(self.FILE_SIZE['blank.vmdk']))

        from COT.commands.add_disk import COTAddDisk
        add_disk = COTAddDisk(UI())
        add_disk.package = intermediate_ovf
        add_disk.output = self.temp_file
        add_disk.disk_image = self.blank_vmdk
        add_disk.file_id = "mydisk"
        add_disk.run()
        self.assertLogged(**self.DRIVE_TYPE_GUESSED_HARDDISK)
        self.assertLogged(**self.CONTROLLER_TYPE_GUESSED_IDE)
        self.assertLogged(**self.OVERWRITING_FILE)
        self.assertLogged(**self.ADDRESS_ON_PARENT_NOT_SPECIFIED)
        add_disk.finished()
        add_disk.destroy()
        self.check_diff(file1=intermediate_ovf, expected="""
 <?xml version='1.0' encoding='utf-8'?>
-<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
+<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" \
xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_ResourceAllocationSettingData">
   <ovf:References>
...
   </ovf:References>
+  <ovf:DiskSection>
+    <ovf:Info>Virtual disk information</ovf:Info>
+    <ovf:Disk ovf:capacity="512" ovf:capacityAllocationUnits="byte * 2^20" \
ovf:diskId="mydisk" ovf:fileRef="mydisk" ovf:format="http://www.vmware.com/\
interfaces/specifications/vmdk.html#streamOptimized" />
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
+        <rasd:HostResource>ovf:/disk/mydisk</rasd:HostResource>
+        <rasd:InstanceID>2</rasd:InstanceID>
+        <rasd:Parent>1</rasd:Parent>
+        <rasd:ResourceType>17</rasd:ResourceType>
+      </ovf:Item>
     </ovf:VirtualHardwareSection>
""")
