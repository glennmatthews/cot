#!/usr/bin/env python
#
# test_qcow2.py - Unit test cases for QCOW2 disk representation.
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

"""Unit test cases for QCOW2 subclass of DiskRepresentation."""

import logging
import os

from COT.tests.ut import COT_UT
from COT.disks import QCOW2

logger = logging.getLogger(__name__)


class TestQCOW2(COT_UT):
    """Test cases for QCOW2 class."""

    def test_init_with_files_unsupported(self):
        """Creation of a QCOW2 with specific file contents is not supported."""
        self.assertRaises(NotImplementedError,
                          QCOW2,
                          path=os.path.join(self.temp_dir, "out.qcow2"),
                          files=[self.input_ovf])
