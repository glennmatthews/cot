#!/usr/bin/env python
#
# edit_properties.py - test cases for the COTEditProperties class
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

import os.path

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.edit_properties import COTEditProperties
from COT.data_validation import ValueUnsupportedError


class TestCOTEditProperties(COT_UT):
    """Unit tests for COTEditProperties submodule"""
    def setUp(self):
        """Test case setup function called automatically prior to each test"""
        super(TestCOTEditProperties, self).setUp()
        self.instance = COTEditProperties(UI())
        self.instance.set_value("output", self.temp_file)

    def test_set_property_value(self):
        """Set the value of an existing property."""
        self.instance.set_value("PACKAGE", self.input_ovf)
        self.instance.set_value("properties", ["login-username=admin"])
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       <ovf:Category>1. Bootstrap Properties</ovf:Category>
-      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" \
ovf:type="string" ovf:userConfigurable="true" ovf:value="">
+      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" \
ovf:type="string" ovf:userConfigurable="true" ovf:value="admin">
         <ovf:Label>Login Username</ovf:Label>
""")

    def test_set_multiple_property_values(self):
        """Set the value of several existing properties."""
        self.instance.set_value("PACKAGE", self.input_ovf)
        self.instance.set_value("properties", ["login-username=admin",
                                               "login-password=cisco123",
                                               "enable-ssh-server=1"])
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       <ovf:Category>1. Bootstrap Properties</ovf:Category>
-      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" \
ovf:type="string" ovf:userConfigurable="true" ovf:value="">
+      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" \
ovf:type="string" ovf:userConfigurable="true" ovf:value="admin">
         <ovf:Label>Login Username</ovf:Label>
...
       </ovf:Property>
-      <ovf:Property ovf:key="login-password" ovf:password="true" \
ovf:qualifiers="MaxLen(25)" ovf:type="string" ovf:userConfigurable="true" \
ovf:value="">
+      <ovf:Property ovf:key="login-password" ovf:password="true" \
ovf:qualifiers="MaxLen(25)" ovf:type="string" ovf:userConfigurable="true" \
ovf:value="cisco123">
         <ovf:Label>Login Password</ovf:Label>
...
       <ovf:Category>2. Features</ovf:Category>
-      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" \
ovf:userConfigurable="true" ovf:value="false">
+      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" \
ovf:userConfigurable="true" ovf:value="true">
         <ovf:Label>Enable SSH Login</ovf:Label>
""")

    def test_create_property(self):
        """Create a new property but do not set its value yet."""
        self.instance.set_value("PACKAGE", self.input_ovf)
        self.instance.set_value("properties", ["new-property-2="])
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       </ovf:Property>
+      <ovf:Property ovf:key="new-property-2" ovf:type="string" ovf:value="" />
     </ovf:ProductSection>
""")

    def test_create_and_set_property(self):
        """Create a new property and set its value"""
        self.instance.set_value("PACKAGE", self.input_ovf)
        self.instance.set_value("properties", ["new-property=hello"])
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       </ovf:Property>
+      <ovf:Property ovf:key="new-property" ovf:type="string" \
ovf:value="hello" />
     </ovf:ProductSection>
""")

    def test_load_config_file(self):
        """Inject a sequence of properties from a config file."""
        self.instance.set_value("PACKAGE", self.input_ovf)
        self.instance.set_value("config_file",
                                os.path.join(os.path.dirname(__file__),
                                             "sample_cfg.txt"))
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       </ovf:Property>
+      <ovf:Property ovf:key="config-0001" ovf:type="string" \
ovf:value="interface GigabitEthernet0/0/0/0" />
+      <ovf:Property ovf:key="config-0002" ovf:type="string" \
ovf:value="no shutdown" />
+      <ovf:Property ovf:key="config-0003" ovf:type="string" \
ovf:value="interface Loopback0" />
+      <ovf:Property ovf:key="config-0004" ovf:type="string" ovf:value="end" />
     </ovf:ProductSection>
""")

    def test_combined(self):
        """Set individual properties AND add from a config file."""
        self.instance.set_value("PACKAGE", self.input_ovf)
        self.instance.set_value("config_file",
                                os.path.join(os.path.dirname(__file__),
                                             "sample_cfg.txt"))
        self.instance.set_value("properties",
                                ["login-password=cisco123",
                                 "enable-ssh-server=1"])
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       </ovf:Property>
-      <ovf:Property ovf:key="login-password" ovf:password="true" \
ovf:qualifiers="MaxLen(25)" ovf:type="string" ovf:userConfigurable="true" \
ovf:value="">
+      <ovf:Property ovf:key="login-password" ovf:password="true" \
ovf:qualifiers="MaxLen(25)" ovf:type="string" ovf:userConfigurable="true" \
ovf:value="cisco123">
         <ovf:Label>Login Password</ovf:Label>
...
       <ovf:Category>2. Features</ovf:Category>
-      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" \
ovf:userConfigurable="true" ovf:value="false">
+      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" \
ovf:userConfigurable="true" ovf:value="true">
         <ovf:Label>Enable SSH Login</ovf:Label>
...
       </ovf:Property>
+      <ovf:Property ovf:key="config-0001" ovf:type="string" \
ovf:value="interface GigabitEthernet0/0/0/0" />
+      <ovf:Property ovf:key="config-0002" ovf:type="string" \
ovf:value="no shutdown" />
+      <ovf:Property ovf:key="config-0003" ovf:type="string" \
ovf:value="interface Loopback0" />
+      <ovf:Property ovf:key="config-0004" ovf:type="string" ovf:value="end" />
     </ovf:ProductSection>
""")

    def test_qualifiers(self):
        """Ensure property values are limited by qualifiers."""

        self.instance.set_value("PACKAGE", self.input_ovf)
        vm = self.instance.vm

        self.assertRaises(ValueUnsupportedError,
                          vm.set_property_value,
                          "login-password",
                          # max length 25 characters according to OVF
                          "abcdefghijklmnopqrstuvwxyz")

        # TODO - we don't currently have any qualifiers other than MaxLen
        # in our example OVF files. Need to get some good samples to use here.

    def test_create_property_no_prexisting(self):
        """Set property values for an OVF that has none previously"""
        self.instance.set_value("PACKAGE", self.minimal_ovf)
        self.instance.set_value("properties", ["hello=world"])
        self.instance.run()
        self.instance.finished()
        self.check_diff(file1=self.minimal_ovf, expected="""
     </ovf:VirtualHardwareSection>
+    <ovf:ProductSection>
+      <ovf:Info>Product Information</ovf:Info>
+      <ovf:Property ovf:key="hello" ovf:type="string" ovf:value="world" />
+    </ovf:ProductSection>
   </ovf:VirtualSystem>
""")

    def test_config_file_not_supported(self):
        """Platform doesn't support literal CLI configuration."""
        self.instance.set_value("PACKAGE", self.iosv_ovf)
        self.instance.set_value("config_file",
                                os.path.join(os.path.dirname(__file__),
                                             "sample_cfg.txt"))
        self.assertRaises(NotImplementedError,
                          self.instance.run)
