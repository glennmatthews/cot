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

"""Unit test cases for COT.edit_properties.COTEditProperties class."""

import logging
import re
from pkg_resources import resource_filename

from COT.tests.ut import COT_UT
from COT.ui_shared import UI
from COT.edit_properties import COTEditProperties
from COT.data_validation import ValueUnsupportedError


class TestCOTEditProperties(COT_UT):
    """Unit tests for COTEditProperties submodule."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCOTEditProperties, self).setUp()
        self.instance = COTEditProperties(UI())
        self.instance.output = self.temp_file

    def test_set_property_value(self):
        """Set the value of an existing property."""
        self.instance.package = self.input_ovf
        self.instance.properties = ["login-username=admin"]
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
        self.instance.package = self.input_ovf
        self.instance.properties = [
            "login-username=admin",
            "login-password=cisco123",
            "enable-ssh-server=1"]
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
        self.instance.package = self.input_ovf
        self.instance.properties = ["new-property-2="]
        self.instance.run()
        self.instance.finished()
        self.check_diff("""
       </ovf:Property>
+      <ovf:Property ovf:key="new-property-2" ovf:type="string" ovf:value="" />
     </ovf:ProductSection>
""")

    def test_create_and_set_property(self):
        """Create a new property and set its value."""
        self.instance.package = self.input_ovf
        self.instance.properties = ["new-property=hello"]
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
        self.instance.package = self.input_ovf
        self.instance.config_file = resource_filename(__name__,
                                                      "sample_cfg.txt")
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
        self.instance.package = self.input_ovf
        self.instance.config_file = resource_filename(__name__,
                                                      "sample_cfg.txt")
        self.instance.properties = ["login-password=cisco123",
                                    "enable-ssh-server=1"]
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
        self.instance.package = self.input_ovf
        vm = self.instance.vm

        self.assertRaises(ValueUnsupportedError,
                          vm.set_property_value,
                          "login-password",
                          # max length 25 characters according to OVF
                          "abcdefghijklmnopqrstuvwxyz")

        # TODO - we don't currently have any qualifiers other than MaxLen
        # in our example OVF files. Need to get some good samples to use here.

    def test_create_property_no_preexisting(self):
        """Set property values for an OVF that has none previously."""
        self.instance.package = self.minimal_ovf
        self.instance.properties = ["hello=world"]
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
        self.instance.package = self.iosv_ovf
        self.instance.config_file = resource_filename(__name__,
                                                      "sample_cfg.txt")
        self.assertRaises(NotImplementedError,
                          self.instance.run)

    def test_edit_interactive(self):
        """Exercise the interactive CLI for COT edit-properties."""
        menu_string = """
Please choose a property to edit:
 1) login-username            "Login Username"
 2) login-password            "Login Password"
 3) mgmt-ipv4-addr            "Management IPv4 Address/Mask"
 4) mgmt-ipv4-gateway         "Management IPv4 Default Gateway"
 5) hostname                  "Router Name"
 6) enable-ssh-server         "Enable SSH Login"
 7) enable-http-server        "Enable HTTP Server"
 8) enable-https-server       "Enable HTTPS Server"
 9) privilege-password        "Enable Password"
10) domain-name               "Domain Name"
Enter property key or number to edit, or 'q' to write changes and quit
        """.strip()

        username_edit_string = """
Key:            "login-username"
Label:          "Login Username"
Description:    "Username for remote login"
Type:           "string"
Qualifiers:     "MaxLen(64)"
Current Value:  ""

Enter new value for this property
        """.strip()

        ssh_edit_string = """
Key:            "enable-ssh-server"
Label:          "Enable SSH Login"
Description:    "Enable remote login via SSH and disable remote login
                 via telnet. Requires login-username and login-
                 password to be set!"
Type:           "boolean"
Qualifiers:     ""
Current Value:  "false"

Enter new value for this property
        """.strip()

        expected_prompts = [
            menu_string,
            username_edit_string,
            menu_string,
            username_edit_string,
            username_edit_string,
            menu_string,
            menu_string,
            re.sub('Value:  ""', 'Value:  "hello"',
                   username_edit_string),
            menu_string,
            menu_string,
            ssh_edit_string,
            ssh_edit_string,
            menu_string
        ]
        custom_inputs = [
            "login-u",     # select by name prefix
            "",            # no change, return to menu
            "1",           # select by number
            ("thisiswaytoolongofastringtouseforausername"
             "whatamipossiblythinking!"),  # invalid value
            "hello",       # valid value, return to menu
            "27",          # out of range
            "1",           # select by number
            "goodbye",     # valid value, return to menu
            "enable-",     # ambiguous selection
            "enable-ssh",  # unambiguous selection
            "nope",        # not a valid boolean
            "true",        # valid boolean
            "q",
        ]
        expected_logs = [
            None,
            {
                'levelname': 'INFO',
                'msg': 'Value.*unchanged',
            },
            None,
            {
                'levelname': 'ERROR',
                'msg': 'Unsupported value.*login-username.*64 characters',
            },
            {
                'levelname': 'INFO',
                'msg': 'Successfully updated property',
            },
            {
                'levelname': 'ERROR',
                'msg': 'Invalid input',
            },
            None,
            {
                'levelname': 'INFO',
                'msg': 'Successfully updated property',
            },
            {
                'levelname': 'ERROR',
                'msg': 'Invalid input',
            },
            None,
            {
                'levelname': 'ERROR',
                'msg': 'Unsupported value.*enable-ssh-server.*boolean',
            },
            {
                'levelname': 'INFO',
                'msg': 'Successfully updated property',
            },
            None,
        ]
        self.counter = 0

        # sanity check
        self.assertEqual(len(expected_prompts), len(custom_inputs),
                         "expected_prompts {0} != custom_inputs {1}"
                         .format(len(expected_prompts), len(custom_inputs)))
        self.assertEqual(len(expected_prompts), len(expected_logs),
                         "expected_prompts {0} != expected_logs {1}"
                         .format(len(expected_prompts), len(expected_logs)))

        def custom_input(prompt, default_value):
            """Mock for get_input."""
            if self.counter > 0:
                log = expected_logs[self.counter-1]
                if log is not None:
                    self.assertLogged(**log)
                else:
                    self.assertNoLogsOver(logging.INFO)
            # Get output and flush it
            # Make sure it matches expectations
            self.maxDiff = None
            self.assertMultiLineEqual(
                expected_prompts[self.counter], prompt,
                "failed at index {0}! Expected:\n{1}\nActual:\n{2}".format(
                    self.counter, expected_prompts[self.counter], prompt))
            # Return our canned input
            input = custom_inputs[self.counter]
            self.counter += 1
            return input

        _input = self.instance.UI.get_input
        try:
            self.instance.UI.get_input = custom_input
            self.instance.package = self.input_ovf
            self.instance.run()
            if expected_logs[self.counter - 1] is not None:
                self.assertLogged(**expected_logs[self.counter - 1])
        finally:
            self.instance.UI.get_input = _input
        self.instance.finished()
        self.check_diff("""
       <ovf:Category>1. Bootstrap Properties</ovf:Category>
-      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" \
ovf:type="string" ovf:userConfigurable="true" ovf:value="">
+      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" \
ovf:type="string" ovf:userConfigurable="true" ovf:value="goodbye">
         <ovf:Label>Login Username</ovf:Label>
...
       <ovf:Category>2. Features</ovf:Category>
-      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" \
ovf:userConfigurable="true" ovf:value="false">
+      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" \
ovf:userConfigurable="true" ovf:value="true">
         <ovf:Label>Enable SSH Login</ovf:Label>
            """)
