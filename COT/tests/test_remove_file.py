#!/usr/bin/env python
#
# test_remove_file.py - test cases for the COTRemoveFile class
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

"""Unit test cases for the COT.remove_file.COTRemoveFile class."""

import os.path

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.remove_file import COTRemoveFile
from COT.data_validation import InvalidInputError, ValueMismatchError


class TestCOTRemoveFile(COT_UT):
    """Test cases for the COTRemoveFile module."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCOTRemoveFile, self).setUp()
        self.instance = COTRemoveFile(UI())
        self.instance.output = self.temp_file

    def test_readiness(self):
        """Test ready_to_run() under various combinations of parameters."""
        self.instance.package = self.input_ovf
        ready, reason = self.instance.ready_to_run()
        self.assertFalse(ready)
        self.assertRegexpMatches(reason, "No file information")
        self.assertRaises(InvalidInputError, self.instance.run)

        self.instance.file_path = "input.vmdk"
        ready, reason = self.instance.ready_to_run()
        self.assertTrue(ready)

        self.instance.file_path = None
        self.instance.file_id = "file1"
        ready, reason = self.instance.ready_to_run()
        self.assertTrue(ready)

    def test_conflicting_args(self):
        """Test conflicting arguments are detected and rejected."""
        self.instance.package = self.input_ovf
        # input.vmdk is file1, file2 is input.iso
        self.instance.file_path = "input.vmdk"
        self.instance.file_id = "file2"
        self.assertRaises(ValueMismatchError, self.instance.run)

    def test_path_nonexistent(self):
        """Test error handling of a file path that isn't in the OVF."""
        self.instance.package = self.input_ovf
        self.instance.file_path = "foobar"
        self.assertRaises(InvalidInputError, self.instance.run)

    def test_id_nonexistent(self):
        """Test error handling of a file id that isn't in the OVF."""
        self.instance.package = self.input_ovf
        self.instance.file_id = "e-dad"
        self.assertRaises(InvalidInputError, self.instance.run)

    def test_text_file_by_path(self):
        """Test deletion of a text file selected by path."""
        self.instance.package = self.input_ovf
        self.instance.file_path = "sample_cfg.txt"
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
-    <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
   </ovf:References>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           cfg_size=self.FILE_SIZE['sample_cfg.txt']))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir,
                                                     "sample_cfg.txt")),
                         "deleted file should not be exported")

    def test_text_file_by_id(self):
        """Test deletion of a text file selected by id."""
        self.instance.package = self.input_ovf
        self.instance.file_id = "textfile"
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
-    <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
   </ovf:References>
""".format(iso_size=self.FILE_SIZE['input.iso'],
           cfg_size=self.FILE_SIZE['sample_cfg.txt']))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir,
                                                     "sample_cfg.txt")),
                         "deleted file should not be exported")

    def test_cdrom(self):
        """Test deletion of a CD-ROM image.

        Because empty CD-ROM drives are permitted, the file is unmapped but
        the device is not deleted.
        """
        self.instance.package = self.input_ovf
        self.instance.file_path = "input.iso"
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
     <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{vmdk_size}" />
-    <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
...
         <rasd:ElementName>CD-ROM 1</rasd:ElementName>
-        <rasd:HostResource>ovf:/file/file2</rasd:HostResource>
         <rasd:InstanceID>7</rasd:InstanceID>
""".format(vmdk_size=self.FILE_SIZE['input.vmdk'],
           iso_size=self.FILE_SIZE['input.iso'],
           cfg_size=self.FILE_SIZE['sample_cfg.txt']))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir,
                                                     "input.iso")),
                         "deleted file should not be exported")

    def test_disk(self):
        """Test deletion of a hard disk.

        Empty hard disk devices are not permitted so the entire disk device
        will be deleted.
        """
        self.instance.package = self.input_ovf
        self.instance.file_id = "file1"
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
   <ovf:References>
-    <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{vmdk_size}" />
     <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
...
     <ovf:Info>Virtual disk information</ovf:Info>
-    <ovf:Disk ovf:capacity="1" ovf:capacityAllocationUnits="byte * 2^30" \
ovf:diskId="vmdisk1" ovf:fileRef="file1" ovf:format="http://www.vmware.com/\
interfaces/specifications/vmdk.html#streamOptimized" />
   </ovf:DiskSection>
...
         <rasd:AddressOnParent>0</rasd:AddressOnParent>
-        <rasd:ElementName>Hard Drive</rasd:ElementName>
-        <rasd:HostResource>ovf:/disk/vmdisk1</rasd:HostResource>
-        <rasd:InstanceID>6</rasd:InstanceID>
-        <rasd:Parent>3</rasd:Parent>
-        <rasd:ResourceType>17</rasd:ResourceType>
-      </ovf:Item>
-      <ovf:Item>
-        <rasd:AddressOnParent>0</rasd:AddressOnParent>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
""".format(vmdk_size=self.FILE_SIZE['input.vmdk'],
           iso_size=self.FILE_SIZE['input.iso']))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir,
                                                     "input.vmdk")),
                         "deleted file should not be exported")
