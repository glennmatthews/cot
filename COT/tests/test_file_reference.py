#!/usr/bin/env python
#
# test_file_reference.py - Unit test cases for COT file reference handling
#
# August 2015, Glenn F. Matthews
# Copyright (c) 2015, 2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for COT.file_reference classes."""

import os
import tarfile

from pkg_resources import resource_filename

from COT.tests import COTTestCase
from COT.file_reference import FileReference, FileOnDisk, FileInTAR


class TestFileReference(COTTestCase):
    """Test cases for abstract FileReference class."""

    def test_create(self):
        """Test create() factory method."""
        fileref = FileReference.create(os.path.dirname(self.input_ovf),
                                       os.path.basename(self.input_ovf))
        self.assertIsInstance(fileref, FileOnDisk)

        fileref = FileReference.create(resource_filename(__name__, "test.tar"),
                                       "sample_cfg.txt")
        self.assertIsInstance(fileref, FileInTAR)

        self.assertRaises(IOError, FileReference.create, "/foo", "bar.txt")
        self.assertRaises(NotImplementedError, FileReference.create,
                          self.input_vmdk, "config.txt")

    def test_create_relative(self):
        """Test create() factory method incorrectly given relative paths."""
        os.chdir(os.path.dirname(self.input_ovf))
        fileref = FileReference.create('.',
                                       os.path.basename(self.input_ovf))
        self.assertIsInstance(fileref, FileOnDisk)
        self.assertLogged(**self.FILE_REF_RELATIVE)

        fileref = FileReference.create("test.tar",
                                       "sample_cfg.txt")
        self.assertIsInstance(fileref, FileInTAR)
        self.assertLogged(**self.FILE_REF_RELATIVE)

        self.assertRaises(IOError, FileReference.create, "/foo", "bar.txt")
        self.assertRaises(NotImplementedError, FileReference.create,
                          self.input_vmdk, "config.txt")


class TestFileOnDisk(COTTestCase):
    """Test cases for FileOnDisk class."""

    def test_nonexistent_file(self):
        """Test error handling when the file doesn't exist."""
        self.assertRaises(IOError, FileOnDisk, "/foo", "bar.txt")

    def test_exists(self):
        """Test the exists property."""
        self.assertTrue(FileOnDisk(os.path.dirname(self.input_ovf),
                                   os.path.basename(self.input_ovf)).exists)
        # false case is covered by test_nonexistent_file

    def test_exists_relative(self):
        """Test like test_exists, but with a relative path."""
        os.chdir(os.path.dirname(self.input_ovf))
        self.assertTrue(FileOnDisk('',
                                   os.path.basename(self.input_ovf)).exists)
        self.assertLogged(**self.FILE_REF_RELATIVE)

    def test_size(self):
        """Test the size property."""
        self.assertEqual(FileOnDisk(os.path.dirname(self.input_ovf),
                                    os.path.basename(self.input_ovf)).size,
                         os.path.getsize(self.input_ovf))

    def test_open(self):
        """Test the open() API."""
        ref = FileOnDisk(os.path.dirname(self.input_ovf),
                         os.path.basename(self.input_ovf))
        with ref.open('r') as ref_obj:
            file_obj = open(self.input_ovf, 'r')
            try:
                self.assertEqual(file_obj.readline(), ref_obj.readline())
            finally:
                file_obj.close()
        # ref_obj should be closed automatically
        self.assertRaises(ValueError, ref_obj.read)

    def test_copy_to(self):
        """Test the copy_to() API."""
        FileOnDisk(os.path.dirname(self.input_ovf),
                   os.path.basename(self.input_ovf)).copy_to(self.temp_dir)
        self.check_diff("", file2=os.path.join(self.temp_dir, 'input.ovf'))

    def test_add_to_archive(self):
        """Test the add_to_archive() API."""
        output_tarfile = os.path.join(self.temp_dir, 'test_output.tar')
        with tarfile.open(output_tarfile, 'w') as tarf:
            FileOnDisk(os.path.dirname(self.input_ovf),
                       os.path.basename(self.input_ovf)).add_to_archive(tarf)
        with tarfile.open(output_tarfile, 'r') as tarf:
            tarf.extract('input.ovf', self.temp_dir)
        self.check_diff("", file2=os.path.join(self.temp_dir, 'input.ovf'))


class TestFileInTAR(COTTestCase):
    """Test cases for FileInTAR class."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestFileInTAR, self).setUp()
        self.tarfile = resource_filename(__name__, "test.tar")
        self.valid_ref = FileInTAR(self.tarfile, "sample_cfg.txt")

    def test_nonexistent_tarfile(self):
        """Test error handling when TAR file doesn't exist."""
        self.assertRaises(IOError, FileInTAR, "/foo/bar", "filename")

    def test_nonexistent_entry(self):
        """Test error handling when filename isn't in the TAR."""
        self.assertRaises(IOError, FileInTAR, self.tarfile, "foo.bar")

    def test_not_tarfile(self):
        """Test error handling when file is not a TAR file."""
        self.assertRaises(IOError, FileInTAR, self.input_ovf, self.input_ovf)

    def test_exists(self):
        """Test the exists property."""
        self.assertTrue(self.valid_ref.exists)
        # false case is covered in test_nonexistent_entry

    def test_exists_relative(self):
        """Test the exists property when initialized with relative path."""
        os.chdir(os.path.dirname(self.tarfile))
        relative_ref = FileInTAR(os.path.basename(self.tarfile),
                                 "sample_cfg.txt")
        self.assertTrue(relative_ref.exists)
        self.assertLogged(**self.FILE_REF_RELATIVE)

    def test_size(self):
        """Test the size property."""
        self.assertEqual(self.valid_ref.size,
                         os.path.getsize(resource_filename(__name__,
                                                           'sample_cfg.txt')))

    def test_open(self):
        """Test the open() API."""
        # open() only supports r/rb mode
        with self.assertRaises(ValueError):
            with self.valid_ref.open('w') as obj:
                assert "Should never get here"
        with self.assertRaises(ValueError):
            with self.valid_ref.open('a') as obj:
                assert "Should never get here"

        with self.valid_ref.open('r') as obj:
            # Check that file contents are as expected
            self.assertEqual(obj.readline(), b'!\n')
            self.assertEqual(obj.readline(),
                             b'interface GigabitEthernet0/0/0/0\n')
        # obj should be closed now
        self.assertRaises(ValueError, obj.read)

    def test_copy_to(self):
        """Test the copy_to() API."""
        self.valid_ref.copy_to(self.temp_dir)
        self.check_diff("",
                        file1=resource_filename(__name__, 'sample_cfg.txt'),
                        file2=os.path.join(self.temp_dir, 'sample_cfg.txt'))

    def test_add_to_archive(self):
        """Test the add_to_archive() API."""
        output_tarfile = os.path.join(self.temp_dir, 'test_output.tar')
        with tarfile.open(output_tarfile, 'w') as tarf:
            self.valid_ref.add_to_archive(tarf)
        with tarfile.open(output_tarfile, 'r') as tarf:
            tarf.extract('sample_cfg.txt', self.temp_dir)
        self.check_diff("",
                        file1=resource_filename(__name__, 'sample_cfg.txt'),
                        file2=os.path.join(self.temp_dir, 'sample_cfg.txt'))
