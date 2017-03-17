# test_generic_platform.py - Unit test cases for COT "generic platform"
#
# October 2016, Glenn F. Matthews
# Copyright (c) 2014-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for the Platform class."""

from COT.platforms.tests import PlatformTests
from COT.platforms.platform import Platform


class TestPlatform(PlatformTests.PlatformTest):
    """Test cases for generic platform handling."""

    cls = Platform
    product_string = ""

    def test_for_product_string(self):
        """Confirm for_product_string() works for an empty string but warns."""
        super(TestPlatform, self).test_for_product_string()
        self.assertLogged(**self.UNRECOGNIZED_PRODUCT_CLASS)
