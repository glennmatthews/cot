#!/usr/bin/env python
#
# test_ovf.py - Unit test cases for COT OVF/OVA handling
#
# September 2013, Glenn F. Matthews
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

"""Unit test cases for COT.vm_description.ovf.OVF class."""

import filecmp
import logging
import os
import os.path
import tempfile
import shutil
import subprocess
import tarfile
import mock

from COT.tests import COTTestCase
from COT.vm_description.ovf import OVF
from COT.vm_description import VMInitError
from COT.data_validation import ValueUnsupportedError
from COT.helpers import helpers, HelperError

logger = logging.getLogger(__name__)


class TestOVFInputOutput(COTTestCase):
    """Test cases for OVF file input/output."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestOVFInputOutput, self).setUp()
        # Additional temp directory used by some test cases
        self.staging_dir = None
        self.base_dir = os.getcwd()

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        if self.staging_dir:
            shutil.rmtree(self.staging_dir)
        os.chdir(self.base_dir)
        super(TestOVFInputOutput, self).tearDown()

    def test_filename_validation(self):
        """Test class method(s) for filename validation."""
        self.assertEqual('.ovf', OVF.detect_type_from_name("/foo/bar/foo.ovf"))
        self.assertEqual('.ova', OVF.detect_type_from_name("/foo/bar/foo.ova"))
        # Lazy filenames should be OK too
        self.assertEqual('.ovf',
                         OVF.detect_type_from_name("/foo/bar/foo.ovf.5.2.2"))
        self.assertLogged(levelname='WARNING',
                          msg="found '%s' in mid-filename; treating as such",
                          args=('foo.ovf.5.2.2', '.ovf'))
        self.assertEqual('.ova',
                         OVF.detect_type_from_name("/foo/bar/foo.ova.15.4.T"))
        self.assertLogged(levelname='WARNING',
                          msg="found '%s' in mid-filename; treating as such",
                          args=('foo.ova.15.4.T', '.ova'))
        # Unsupported formats
        self.assertRaises(ValueUnsupportedError, OVF.detect_type_from_name,
                          "/foo/bar.ovf/baz")
        self.assertRaises(ValueUnsupportedError, OVF.detect_type_from_name,
                          "/foo/bar.zip")

    def test_input_output(self):
        """Read an OVF then write it again, verify no changes."""
        with OVF(self.input_ovf, self.temp_file) as vm:
            self.assertEqual(vm.ovf_version, 1.0)
        self.check_diff('')
        self.check_diff(
            file1=self.input_manifest,
            file2=os.path.join(self.temp_dir, "out.mf"),
            expected="""
-SHA1(input.ovf)= c3bd2579c2edc76ea35b5bde7d4f4e41eab08963
+SHA1(out.ovf)= c3bd2579c2edc76ea35b5bde7d4f4e41eab08963
 SHA1(input.vmdk)= 264caaa216ad928f82f727bb06d8e6e6fbd94df0
 """)

        # Filename output too
        with OVF(self.input_ovf, self.temp_file + '.a.b.c'):
            self.assertLogged(
                levelname='WARNING',
                msg="found '%s' in mid-filename; treating as such",
                args=('out.ovf.a.b.c', '.ovf'))
        self.check_diff('', file2=(self.temp_file + ".a.b.c"))

    def test_input_output_relative_paths(self):
        """Make sure relative and implicit paths are handled."""
        os.chdir(os.path.dirname(self.input_ovf))
        with OVF(os.path.basename(self.input_ovf), self.temp_file) as vm:
            self.assertEqual(vm.ovf_version, 1.0)
        self.check_diff('')
        os.remove(self.temp_file)

        with OVF(os.path.join(".", os.path.basename(self.input_ovf)),
                 self.temp_file) as vm:
            self.assertEqual(vm.ovf_version, 1.0)
        self.check_diff('')
        os.remove(self.temp_file)

        os.chdir(os.path.dirname(self.temp_file))
        with OVF(self.input_ovf, os.path.basename(self.temp_file)) as vm:
            self.assertEqual(vm.ovf_version, 1.0)
        self.check_diff('')
        os.remove(self.temp_file)

        with OVF(self.input_ovf,
                 os.path.join(".", os.path.basename(self.temp_file))) as vm:
            self.assertEqual(vm.ovf_version, 1.0)
        self.check_diff('')

    def test_input_output_v09(self):
        """Test reading/writing of a v0.9 OVF."""
        with OVF(self.v09_ovf, self.temp_file) as vm:
            self.assertEqual(vm.ovf_version, 0.9)
        self.check_diff('', file1=self.v09_ovf)

    def test_input_output_v20_vbox(self):
        """Test reading/writing of a v2.0 OVF from VirtualBox."""
        with OVF(self.v20_vbox_ovf, self.temp_file) as vm:
            self.assertEqual(vm.ovf_version, 2.0)

        # TODO - vbox XML is not very clean so the diffs are large...
        # self.check_diff('', file1=self.v20_vbox_ovf)

        # ovftool does not consider vbox ovfs to be valid
        self.validate_output_with_ovftool = False

        # TODO - similarly OVF checksum will change, so a direct check
        # of the manifest is out
        # self.check_diff(file1=self.v20_vbox_manifest,
        #                 file2=os.path.join(self.temp_dir, "out.mf"),
        #                 expected="")

    def test_input_output_vmware(self):
        """Test reading/writing of an OVF with custom extensions."""
        with OVF(self.vmware_ovf, self.temp_file):
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
        shutil.copy(self.sample_cfg, self.staging_dir)
        # Don't copy input.iso to the staging directory.
        with OVF(os.path.join(self.staging_dir, 'input.ovf'), self.temp_file):
            self.assertLogged(**self.NONEXISTENT_FILE)
        self.assertLogged(**self.REMOVING_FILE)
        self.check_diff("""
     <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{vmdk_size}" />
-    <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
""".format(vmdk_size=self.FILE_SIZE['input.vmdk'],
           iso_size=self.FILE_SIZE['input.iso'],
           cfg_size=self.FILE_SIZE['sample_cfg.txt']))

        # Read-only OVF
        with OVF(os.path.join(self.staging_dir, 'input.ovf'), None):
            self.assertLogged(**self.NONEXISTENT_FILE)

        # File exists at read time but has disappeared by write time
        shutil.copy(self.input_iso, self.staging_dir)
        with OVF(os.path.join(self.staging_dir, 'input.ovf'), self.temp_file):
            os.remove(os.path.join(self.staging_dir, 'input.iso'))
        self.assertLogged(**self.FILE_DISAPPEARED)
        self.assertLogged(**self.REMOVING_FILE)
        self.check_diff("""
     <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{vmdk_size}" />
-    <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
""".format(vmdk_size=self.FILE_SIZE['input.vmdk'],
           iso_size=self.FILE_SIZE['input.iso'],
           cfg_size=self.FILE_SIZE['sample_cfg.txt']))

        # Read OVA, write OVF
        with tarfile.open(os.path.join(self.staging_dir, 'input.ova'),
                          'w') as tarf:
            tarf.add(os.path.join(self.staging_dir, 'input.ovf'), 'input.ovf')
            tarf.add(os.path.join(self.staging_dir, 'input.vmdk'),
                     'input.vmdk')
            tarf.add(self.sample_cfg, 'sample_cfg.txt')
        with OVF(os.path.join(self.staging_dir, 'input.ova'),
                 os.path.join(self.temp_dir, 'output.ovf')):
            self.assertLogged(**self.NONEXISTENT_FILE)
        self.assertLogged(**self.REMOVING_FILE)
        self.check_diff(file2=os.path.join(self.temp_dir, 'output.ovf'),
                        expected="""
     <ovf:File ovf:href="input.vmdk" ovf:id="file1" ovf:size="{vmdk_size}" />
-    <ovf:File ovf:href="input.iso" ovf:id="file2" ovf:size="{iso_size}" />
     <ovf:File ovf:href="sample_cfg.txt" ovf:id="textfile" \
ovf:size="{cfg_size}" />
""".format(vmdk_size=self.FILE_SIZE['input.vmdk'],
           iso_size=self.FILE_SIZE['input.iso'],
           cfg_size=self.FILE_SIZE['sample_cfg.txt']))

        # Also test read-only OVA logic:
        with OVF(os.path.join(self.staging_dir, "input.ova"), None):
            self.assertLogged(**self.NONEXISTENT_FILE)

    def test_input_output_bad_file(self):
        """Test reading/writing of an OVF with incorrect file references."""
        self.staging_dir = tempfile.mkdtemp(prefix="cot_ut_ovfio_stage")
        input_dir = os.path.dirname(self.input_ovf)
        shutil.copy(os.path.join(input_dir, 'input.ovf'), self.staging_dir)
        shutil.copy(os.path.join(input_dir, 'input.iso'), self.staging_dir)
        shutil.copy(self.sample_cfg, self.staging_dir)
        # Copy blank.vmdk to input.vmdk so as to have the wrong size/checksum
        shutil.copy(self.blank_vmdk,
                    os.path.join(self.staging_dir, 'input.vmdk'))
        with OVF(os.path.join(self.staging_dir, 'input.ovf'),
                 os.path.join(self.temp_dir, "temp.ova")):
            # Write out to OVA (which will correct the file size information)
            pass
        self.assertLogged(msg="The size of file '%s' is expected"
                          " to be.*but is actually.*")
        self.assertLogged(msg="Capacity of disk.*seems to have changed.*"
                          "The updated OVF will reflect this change.")

        # Now read in the OVA
        with OVF(os.path.join(self.temp_dir, "temp.ova"),
                 os.path.join(self.temp_dir, "temp.ovf")):
            # Replace the tar file fake .vmdk with the real .vmdk
            with tarfile.open(os.path.join(self.temp_dir, "temp.ova"),
                              'a') as tarf:
                tarf.add(self.input_vmdk, 'input.vmdk')

        self.assertLogged(msg="Size of file '%s' has changed")
        self.assertLogged(msg="checksum of file '%s' has changed")
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

        # Read OVA and overwrite itself
        # Issue #66 resulted from the two strings not being identical
        # So mix relative and absolute paths:
        os.chdir(self.temp_dir)
        ova = OVF("temp.ova",
                  os.path.join(self.temp_dir, "temp.ova"))
        ova.write()
        ova.destroy()

        # Another permutation of issue #66 - output file is a
        # symlink to input file
        os.symlink("temp.ova", "symlink.ova")
        ova = OVF("temp.ova", "symlink.ova")
        ova.write()
        ova.destroy()

        # A third permutation - output file is hardlink to input
        os.link("temp.ova", "hardlink.ova")
        ova = OVF("temp.ova", "hardlink.ova")
        ova.write()
        ova.destroy()

        # Read OVA and write to OVF
        ovf2 = OVF(os.path.join(self.temp_dir, "temp.ova"),
                   os.path.join(self.temp_dir, "input.ovf"))
        ovf2.write()
        ovf2.destroy()

        # Make sure everything propagated over successfully
        input_dir = os.path.dirname(self.input_ovf)
        for ext in ['.ovf', '.mf', '.iso', '.vmdk']:
            if ext == '.mf' or ext == '.ovf':
                self.check_diff("", os.path.join(input_dir, "input" + ext),
                                os.path.join(self.temp_dir, "input" + ext))
            else:
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
        shutil.copy(self.sample_cfg, self.staging_dir)
        ovf = OVF(os.path.join(self.staging_dir, 'input.ovf'),
                  os.path.join(self.temp_dir, 'input.ova'))
        ovf.write()
        ovf.destroy()

        with tarfile.open(os.path.join(self.temp_dir, 'input.ova'),
                          'r') as tarf:
            try:
                vmdk = tarf.getmember('input.vmdk')
                self.assertTrue(vmdk.isfile(),
                                "hardlink was not added as a regular file")
                self.assertFalse(vmdk.islnk())
                iso = tarf.getmember('input.iso')
                self.assertTrue(iso.isfile(),
                                "symlink was not added as a regular file")
                self.assertFalse(iso.issym())
            except KeyError as exc:
                self.fail("KeyError: {0}\n Tarfile members = {1}"
                          .format(exc, tarf.getnames()))

    def test_invalid_ovf_file(self):
        """Check that various invalid input OVF files result in VMInitError."""
        fake_file = os.path.join(self.temp_dir, "foo.ovf")
        # .ovf that is an empty file
        with open(fake_file, 'w') as fileobj:
            fileobj.write("")
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ovf that isn't actually XML at all
        with open(fake_file, 'w') as fileobj:
            fileobj.write("< hello world!")
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ovf that is XML but not OVF XML
        with open(fake_file, 'w') as fileobj:
            fileobj.write("<?xml version='1.0' encoding='utf-8'?>")
        self.assertRaises(VMInitError, OVF, fake_file, None)
        with open(fake_file, 'w') as fileobj:
            fileobj.write("<?xml version='1.0' encoding='utf-8'?>")
            fileobj.write("<foo/>")
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ovf claiming to be OVF version 3.0, which doesn't exist yet
        with self.assertRaises(VMInitError) as catcher:
            OVF(self.ersatz_v3_ovf, None)
        self.assertEqual(catcher.exception.errno, 2)
        self.assertEqual(catcher.exception.strerror,
                         "File has an Envelope but it is in unknown namespace "
                         "'http://schemas.dmtf.org/ovf/envelope/3'")
        self.assertEqual(catcher.exception.filename, self.ersatz_v3_ovf)

    @mock.patch("COT.vm_description.ovf.OVF.detect_type_from_name",
                return_value=".vbox")
    def test_unknown_extension(self, mock_type):
        # pylint: disable=missing-type-doc,missing-param-doc
        """Test handling of unexpected behavior in detect_type_from_name."""
        # unsupported input file type
        with self.assertRaises(VMInitError) as catcher:
            OVF(self.input_ovf, None)
        self.assertEqual(catcher.exception.errno, 2)
        self.assertEqual(catcher.exception.strerror,
                         "File does not appear to be an OVA or OVF")
        self.assertEqual(catcher.exception.filename, self.input_ovf)

        # unsupported output file type
        mock_type.return_value = ".ovf"
        with self.assertRaises(NotImplementedError) as catcher, \
                OVF(self.input_ovf, None) as vm:
            mock_type.return_value = ".qcow2"
            vm.output_file = os.path.join(self.temp_dir, "foo.qcow2")

        self.assertEqual(catcher.exception.args[0],
                         "Not sure how to write a '.qcow2' file")

    def test_invalid_ova_file(self):
        """Check that various invalid input OVA files result in VMInitError."""
        fake_file = os.path.join(self.temp_dir, "foo.ova")
        # .ova that is an empty file
        with open(fake_file, 'w') as fileobj:
            fileobj.write("")
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ova that is not a TAR file
        with open(fake_file, 'w') as fileobj:
            fileobj.write("< hello world!")
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ova that is an empty TAR file
        with tarfile.open(fake_file, 'w') as tarf:
            pass
        with self.assertRaises(VMInitError) as catcher:
            OVF(fake_file, None)
        self.assertEqual(catcher.exception.errno, 1)
        self.assertEqual(catcher.exception.strerror, "No files to untar")
        self.assertEqual(catcher.exception.filename, fake_file)

        # .ova that is a TAR file but does not contain an OVF descriptor
        with tarfile.open(fake_file, 'w') as tarf:
            tarf.add(self.blank_vmdk, os.path.basename(self.blank_vmdk))
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # .ova that contains an OVF descriptor but in the wrong position
        with tarfile.open(fake_file, 'a') as tarf:
            tarf.add(self.minimal_ovf, os.path.basename(self.minimal_ovf))
        # this results in a logged error but not rejection - Postel's Law
        with OVF(fake_file, None):
            self.assertLogged(
                levelname="ERROR",
                msg="OVF file %s found, but .*not.*first")

        # .ova with unsafe absolute path references
        with tarfile.open(fake_file, 'w') as tarf:
            # tarfile.add() is sometimes smart enough to protect us against
            # such unsafe references, but we can overrule it by using
            # gettarinfo() and addfile() instead of just add().
            tari = tarf.gettarinfo(self.minimal_ovf)
            tari.name = os.path.abspath(
                os.path.join(os.path.dirname(self.minimal_ovf),
                             "..", "..", "..",
                             os.path.basename(self.minimal_ovf)))
            with open(self.minimal_ovf, 'rb') as fileobj:
                tarf.addfile(tari, fileobj)
        self.assertRaises(VMInitError, OVF, fake_file, None)

    def test_invalid_ovf_contents(self):
        """Check for rejection of OVF files with valid XML but invalid data."""
        # Multiple Items under same profile with same InstanceID
        fake_file = os.path.join(self.temp_dir, "foo.ovf")
        with open(fake_file, "w") as fileobj:
            subprocess.check_call(['sed', 's/InstanceID>11</InstanceID>10</',
                                   self.input_ovf],
                                  stdout=fileobj)
        if helpers['ovftool']:
            # Make sure ovftool also sees this as invalid
            self.assertRaises(HelperError,
                              helpers['ovftool'].call,
                              ['--schemaValidate', fake_file])
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # Item referencing a nonexistent Configuration
        with open(fake_file, "w") as fileobj:
            subprocess.check_call(['sed', 's/on="2CPU-2GB-1NIC"/on="foo"/',
                                   self.input_ovf],
                                  stdout=fileobj)
        if helpers['ovftool']:
            # Make sure ovftool also sees this as invalid
            self.assertRaises(HelperError,
                              helpers['ovftool'].call,
                              ['--schemaValidate', fake_file])
        self.assertRaises(VMInitError, OVF, fake_file, None)

        # TODO - inconsistent order of File versus Disk?
        # TODO - Sections in wrong order?


class TestOVFAPI(COTTestCase):
    """Test cases for OVF APIs."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestOVFAPI, self).setUp()
        # Output to OVA instead of OVF by default
        self.temp_file = os.path.join(self.temp_dir, "out.ova")

    def test_predicted_output_size(self):
        """Check output size prediction against reality."""
        self.validate_output_with_ovftool = False
        for input_file in [
                self.input_ovf,
                self.minimal_ovf,
                self.iosv_ovf,
                self.v09_ovf,
                self.v20_vbox_ovf,
                self.vmware_ovf,
        ]:
            with OVF(input_file, self.temp_file) as ovf:
                predicted = ovf.predicted_output_size()
            actual = os.stat(self.temp_file).st_size
            # Up to 10% greater than reality is OK,
            # but aim for never less than.
            self.assertGreaterEqual(
                predicted, actual,
                "predicted output size of {0} was {1} but actual size is {2}"
                .format(input_file, predicted, actual))
            self.assertLessEqual(
                predicted, int(actual * 1.1),
                "predicted output size of {0} was {1} but actual size is {2}"
                .format(input_file, predicted, actual))

    def test_configuration_profiles(self):
        """Check profile id list APIs."""
        # No profiles defined
        with OVF(self.vmware_ovf, None) as ovf:
            self.assertEqual(ovf.config_profiles, [])
            self.assertEqual(ovf.default_config_profile, None)

        # Profile list exists
        with OVF(self.input_ovf, None) as ovf:
            # default profile is first in the list
            self.assertEqual(ovf.config_profiles,
                             ["4CPU-4GB-3NIC",
                              "1CPU-1GB-1NIC",
                              "2CPU-2GB-1NIC"])
            self.assertEqual(ovf.default_config_profile, "4CPU-4GB-3NIC")

    def test_find_empty_drive_unsupported(self):
        """Negative test for find_empty_drive()."""
        with OVF(self.input_ovf, None) as ovf:
            self.assertRaises(ValueUnsupportedError,
                              ovf.find_empty_drive, 'floppy')
