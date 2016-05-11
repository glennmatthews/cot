#!/usr/bin/env python
#
# test_file_reference.py - Unit test cases for COT file reference handling
#
# August 2015, Glenn F. Matthews
# Copyright (c) 2015 the COT project developers.
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

from contextlib import closing
from pkg_resources import resource_filename

from COT.tests.ut import COT_UT
from COT.file_reference import FileOnDisk, FileInTAR


class TestFileOnDisk(COT_UT):
    """Test cases for FileOnDisk class."""

    def test_nonexistent_file(self):
        """Test error handling when the file doesn't exist."""
        self.assertRaises(IOError, FileOnDisk, "/foo/bar.txt")
        self.assertRaises(IOError, FileOnDisk, "/foo", "bar.txt")

    def test_exists(self):
        """Test the exists() API."""
        self.assertTrue(FileOnDisk(self.input_ovf).exists())
        # false case is covered by test_nonexistent_file

    def test_size(self):
        """Test the size() API."""
        self.assertEqual(FileOnDisk(self.input_ovf).size(),
                         os.path.getsize(self.input_ovf))

    def test_open_close(self):
        """Test the open() and close() APIs."""
        ref = FileOnDisk(self.input_ovf)
        ref_obj = ref.open('r')
        try:
            file_obj = open(self.input_ovf, 'r')
            try:
                self.assertEqual(file_obj.readline(), ref_obj.readline())
            finally:
                file_obj.close()
        finally:
            ref.close()

    def test_copy_to(self):
        """Test the copy_to() API."""
        FileOnDisk(self.input_ovf).copy_to(self.temp_dir)
        self.check_diff("", file2=os.path.join(self.temp_dir, 'input.ovf'))

    def test_add_to_archive(self):
        """Test the add_to_archive() API."""
        output_tarfile = os.path.join(self.temp_dir, 'test_output.tar')
        with closing(tarfile.open(output_tarfile, 'w')) as tarf:
            FileOnDisk(self.input_ovf).add_to_archive(tarf)
        with closing(tarfile.open(output_tarfile, 'r')) as tarf:
            tarf.extract('input.ovf', self.temp_dir)
        self.check_diff("", file2=os.path.join(self.temp_dir, 'input.ovf'))


class TestFileInTAR(COT_UT):
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
        """Test the exists() API."""
        self.assertTrue(self.valid_ref.exists())
        # false case is covered in test_nonexistent_entry

    def test_size(self):
        """Test the size() API."""
        self.assertEqual(self.valid_ref.size(),
                         os.path.getsize(resource_filename(__name__,
                                                           'sample_cfg.txt')))

    def test_open_close(self):
        """Test the open() and close() APIs."""
        # open() only supports r/rb mode
        self.assertRaises(ValueError, self.valid_ref.open, 'w')
        self.assertRaises(ValueError, self.valid_ref.open, 'a')

        # No-op:
        self.valid_ref.close()

        obj = self.valid_ref.open('r')
        # Check that file contents are as expected
        self.assertEqual(obj.readline(), b'!\n')
        self.assertEqual(obj.readline(), b'interface GigabitEthernet0/0/0/0\n')
        # TODO: this should clean up nicely
        obj.close()
        self.valid_ref.close()
        self.assertRaises(ValueError, obj.read)
        # No-op:
        self.valid_ref.close()

    def test_copy_to(self):
        """Test the copy_to() API."""
        self.valid_ref.copy_to(self.temp_dir)
        self.check_diff("",
                        file1=resource_filename(__name__, 'sample_cfg.txt'),
                        file2=os.path.join(self.temp_dir, 'sample_cfg.txt'))

    def test_add_to_archive(self):
        """Test the add_to_archive() API."""
        output_tarfile = os.path.join(self.temp_dir, 'test_output.tar')
        with closing(tarfile.open(output_tarfile, 'w')) as tarf:
            self.valid_ref.add_to_archive(tarf)
        with closing(tarfile.open(output_tarfile, 'r')) as tarf:
            tarf.extract('sample_cfg.txt', self.temp_dir)
        self.check_diff("",
                        file1=resource_filename(__name__, 'sample_cfg.txt'),
                        file2=os.path.join(self.temp_dir, 'sample_cfg.txt'))
