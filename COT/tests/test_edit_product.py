#!/usr/bin/env python
#
# edit_product.py - test cases for the COTEditProduct class
#
# January 2015, Glenn F. Matthews
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

"""Unit test cases for the COT.edit_product.COTEditProduct class."""

import re

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.edit_product import COTEditProduct
from COT.data_validation import InvalidInputError


class TestCOTEditProduct(COT_UT):

    """Unit tests for COTEditProduct submodule."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCOTEditProduct, self).setUp()
        self.instance = COTEditProduct(UI())
        self.instance.output = self.temp_file

    def test_readiness(self):
        """Test ready_to_run() under various combinations of parameters."""
        ready, reason = self.instance.ready_to_run()
        self.assertFalse(ready)
        self.assertEqual("PACKAGE is a mandatory argument!", reason)
        self.assertRaises(InvalidInputError, self.instance.run)

        self.instance.package = self.input_ovf
        ready, reason = self.instance.ready_to_run()
        self.assertFalse(ready)
        self.assertTrue(re.search("nothing to do", reason))
        self.assertRaises(InvalidInputError, self.instance.run)

        self.instance.version = "X"
        ready, reason = self.instance.ready_to_run()
        self.assertTrue(ready)

        self.instance.version = None
        self.instance.full_version = "Y"
        ready, reason = self.instance.ready_to_run()
        self.assertTrue(ready)

        self.instance.full_version = None
        ready, reason = self.instance.ready_to_run()
        self.assertFalse(ready)
        self.assertTrue(re.search("nothing to do", reason))
        self.assertRaises(InvalidInputError, self.instance.run)

    def test_edit_short_version(self):
        """Editing the short version alone."""
        self.instance.package = self.input_ovf
        self.instance.version = "5.3.1"
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       <ovf:Vendor>Cisco Systems, Inc.</ovf:Vendor>
-      <ovf:Version>DEV</ovf:Version>
+      <ovf:Version>5.3.1</ovf:Version>
       <ovf:FullVersion>DEVELOPMENT IMAGE</ovf:FullVersion>
""")

    def test_edit_full_version(self):
        """Editing the full version alone."""
        self.instance.package = self.input_ovf
        self.instance.full_version = "Some arbitrary product, version 3.14159"
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       <ovf:Version>DEV</ovf:Version>
-      <ovf:FullVersion>DEVELOPMENT IMAGE</ovf:FullVersion>
+      <ovf:FullVersion>Some arbitrary product, version 3.14159\
</ovf:FullVersion>
       <ovf:ProductUrl>http://www.cisco.com/en/US/products/ps12559/index.html\
</ovf:ProductUrl>
""")

    def test_edit_full_no_existing(self):
        """Edit full version in an OVF with no previous values."""
        self.instance.package = self.minimal_ovf
        self.instance.full_version = "Full Version"
        self.instance.run()
        self.instance.finished()
        self.check_diff(file1=self.minimal_ovf,
                        expected="""
     </ovf:VirtualHardwareSection>
+    <ovf:ProductSection>
+      <ovf:Info>Product Information</ovf:Info>
+      <ovf:FullVersion>Full Version</ovf:FullVersion>
+    </ovf:ProductSection>
   </ovf:VirtualSystem>
""")

    def test_edit_both_versions(self):
        """Edit both version strings."""
        self.instance.package = self.input_ovf
        self.instance.version = "5.2.0.01I"
        self.instance.full_version = "Cisco IOS XRv, Version 5.2"
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       <ovf:Vendor>Cisco Systems, Inc.</ovf:Vendor>
-      <ovf:Version>DEV</ovf:Version>
-      <ovf:FullVersion>DEVELOPMENT IMAGE</ovf:FullVersion>
+      <ovf:Version>5.2.0.01I</ovf:Version>
+      <ovf:FullVersion>Cisco IOS XRv, Version 5.2</ovf:FullVersion>
       <ovf:ProductUrl>http://www.cisco.com/en/US/products/ps12559/index.html\
</ovf:ProductUrl>
""")

    def test_edit_both_no_existing(self):
        """Edit both version strings in an OVF with no previous values."""
        self.instance.package = self.minimal_ovf
        self.instance.version = "Version"
        self.instance.full_version = "Full Version"
        self.instance.run()
        self.instance.finished()
        self.check_diff(file1=self.minimal_ovf,
                        expected="""
     </ovf:VirtualHardwareSection>
+    <ovf:ProductSection>
+      <ovf:Info>Product Information</ovf:Info>
+      <ovf:Version>Version</ovf:Version>
+      <ovf:FullVersion>Full Version</ovf:FullVersion>
+    </ovf:ProductSection>
   </ovf:VirtualSystem>
""")
