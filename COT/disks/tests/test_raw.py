#!/usr/bin/env python
#
# test_raw.py - Unit test cases for RAW disk representation.
#
# October 2016, Glenn F. Matthews
# Copyright (c) 2014-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for RAW subclass of DiskRepresentation."""

import logging
import os

from COT.tests.ut import COT_UT
from COT.disks import RAW, disk_representation_from_file

logger = logging.getLogger(__name__)


class TestRAW(COT_UT):
    """Test cases for RAW disk image representation."""

    def test_convert_from_vmdk(self):
        """Test conversion of a RAW image from a VMDK."""
        old = disk_representation_from_file(self.blank_vmdk)
        raw = RAW.from_other_image(old, self.temp_dir)

        self.assertEqual(raw.disk_format, 'raw')
        self.assertEqual(raw.disk_subformat, None)

    def test_create_with_capacity(self):
        """Creation of a raw image of a particular size."""
        raw = RAW(path=os.path.join(self.temp_dir, "out.raw"),
                  capacity="16M")
        self.assertEqual(raw.disk_format, 'raw')
        self.assertEqual(raw.disk_subformat, None)

    def test_create_with_files(self):
        """Creation of a raw image with specific file contents."""
        raw = RAW(path=os.path.join(self.temp_dir, "out.img"),
                  files=[self.input_ovf])
        self.assertEqual(raw.files,
                         [os.path.basename(self.input_ovf)])
        self.assertEqual(raw.capacity, "8388608")

    def test_create_with_files_and_capacity(self):
        """Creation of raw image with specified capacity and file contents."""
        raw = RAW(path=os.path.join(self.temp_dir, "out.img"),
                  files=[self.input_ovf],
                  capacity="64M")
        self.assertEqual(raw.files,
                         [os.path.basename(self.input_ovf)])
        self.assertEqual(raw.capacity, "67108864")
