#!/usr/bin/env python
#
# edit_properties.py - test cases for the COTEditProperties class
#
# January 2015, Glenn F. Matthews
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

"""Unit test cases for COT.edit_properties.COTEditProperties class."""

import logging
import re

from COT.commands.tests.command_testcase import CommandTestCase
from COT.commands.edit_properties import COTEditProperties
from COT.data_validation import ValueUnsupportedError


class TestCOTEditProperties(CommandTestCase):
    """Unit tests for COTEditProperties command."""

    command_class = COTEditProperties

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCOTEditProperties, self).setUp()
        self.counter = 0

    def test_not_ready_to_run_labels(self):
        """Test ready_to_run() failure scenarios involving the --label opt."""
        self.command.package = self.input_ovf
        # --label requires --properties
        self.command.labels = ["label1", "label2"]
        ready, reason = self.command.ready_to_run()
        self.assertFalse(ready)
        self.assertRegex(reason, r"--label.*requires.*--properties")
        # --label and --properties must have the same number of params
        self.command.properties = ["foo=bar"]
        ready, reason = self.command.ready_to_run()
        self.assertFalse(ready)
        self.assertRegex(reason, r"--label.*\(2\).*--properties \(1\)")

    def test_not_ready_to_run_descriptions(self):
        """Test ready_to_run() failure scenarios involving the --desc opt."""
        self.command.package = self.input_ovf
        # --desc requires --properties
        self.command.descriptions = ["desc1", "desc2"]
        ready, reason = self.command.ready_to_run()
        self.assertFalse(ready)
        self.assertRegex(reason, r"--description.*requires.*--properties")
        # --desc and --properties must have the same number of params
        self.command.properties = ["foo=bar"]
        ready, reason = self.command.ready_to_run()
        self.assertFalse(ready)
        self.assertRegex(reason, r"--description.*\(2\).*--properties \(1\)")

    def test_set_property_value(self):
        """Set the value of an existing property."""
        self.command.package = self.input_ovf
        self.command.properties = ["login-username=admin"]
        self.command.run()
        self.command.finished()
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
        self.command.package = self.input_ovf
        self.command.properties = [
            "login-username=admin",
            "login-password=cisco123",
            "enable-ssh-server=1"]
        self.command.run()
        self.command.finished()
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
        """Create new properties but do not set their values yet."""
        self.command.package = self.input_ovf
        self.command.properties = [
            "new-property-2=",    # default value is empty string
            "new-property-3",     # no default value
        ]
        self.command.run()
        self.command.finished()
        self.check_diff("""
       </ovf:Property>
+      <ovf:Property ovf:key="new-property-2" ovf:type="string" ovf:value="" />
+      <ovf:Property ovf:key="new-property-3" ovf:type="string" />
     </ovf:ProductSection>
""")

    def test_create_and_set_property(self):
        """Create a new property and set its value."""
        self.command.package = self.input_ovf
        self.command.properties = ["new-property=hello"]
        self.command.run()
        self.command.finished()
        self.check_diff("""
       </ovf:Property>
+      <ovf:Property ovf:key="new-property" ovf:type="string" \
ovf:value="hello" />
     </ovf:ProductSection>
""")

    def test_create_property_variants(self):
        """Variant options for creating new properties."""
        self.command.package = self.input_ovf
        self.command.properties = [
            "empty-property",
            "property-with-value=value",
            "prop-with-type+string",
            "prop-with-value-and-type=yes+boolean",
        ]
        self.command.run()
        self.command.finished()
        self.check_diff("""
       </ovf:Property>
+      <ovf:Property ovf:key="empty-property" ovf:type="string" />
+      <ovf:Property ovf:key="property-with-value" ovf:type="string" \
ovf:value="value" />
+      <ovf:Property ovf:key="prop-with-type" ovf:type="string" />
+      <ovf:Property ovf:key="prop-with-value-and-type" ovf:type="boolean" \
ovf:value="true" />
     </ovf:ProductSection>
""")

    def test_change_type_existing_invalid(self):
        """Change the type of an existing property so that value is invalid."""
        self.command.package = self.invalid_ovf
        self.assertLogged(**self.UNRECOGNIZED_PRODUCT_CLASS)
        self.assertLogged(**self.NONEXISTENT_FILE)
        self.command.properties = ['jabberwock+boolean']
        with self.assertRaises(ValueUnsupportedError):
            self.command.run()

    def test_create_edit_and_user_configurable(self):
        """Create new props, edit existing, and set user-configable flag."""
        self.command.package = self.input_ovf
        self.command.properties = [
            'new-property=false+boolean',
            'domain-name=example.com',
            'another-new=yep!',
            'enable-https-server+string',
        ]
        self.command.user_configurable = False
        self.command.run()
        self.command.finished()
        self.check_diff("""
       </ovf:Property>
-      <ovf:Property ovf:key="enable-https-server" ovf:type="boolean" \
ovf:userConfigurable="true" ovf:value="false">
+      <ovf:Property ovf:key="enable-https-server" ovf:type="string" \
ovf:userConfigurable="false" ovf:value="false">
         <ovf:Label>Enable HTTPS Server</ovf:Label>
...
       </ovf:Property>
-      <ovf:Property ovf:key="domain-name" ovf:qualifiers="MaxLen(238)" \
ovf:type="string" ovf:userConfigurable="true" ovf:value="">
+      <ovf:Property ovf:key="domain-name" ovf:qualifiers="MaxLen(238)" \
ovf:type="string" ovf:userConfigurable="false" ovf:value="example.com">
         <ovf:Label>Domain Name</ovf:Label>
...
       </ovf:Property>
+      <ovf:Property ovf:key="new-property" ovf:type="boolean" \
ovf:userConfigurable="false" ovf:value="false" />
+      <ovf:Property ovf:key="another-new" ovf:type="string" \
ovf:userConfigurable="false" ovf:value="yep!" />
     </ovf:ProductSection>
""")

    def test_load_config_file(self):
        """Inject a sequence of properties from a config file."""
        self.command.package = self.input_ovf
        self.command.config_file = self.sample_cfg
        self.command.run()
        self.command.finished()
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
        self.command.package = self.input_ovf
        self.command.config_file = self.sample_cfg
        self.command.properties = ["login-password=cisco123",
                                   "enable-ssh-server=1"]
        self.command.user_configurable = True
        self.command.run()
        self.command.finished()
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
ovf:userConfigurable="true" ovf:value="interface GigabitEthernet0/0/0/0" />
+      <ovf:Property ovf:key="config-0002" ovf:type="string" \
ovf:userConfigurable="true" ovf:value="no shutdown" />
+      <ovf:Property ovf:key="config-0003" ovf:type="string" \
ovf:userConfigurable="true" ovf:value="interface Loopback0" />
+      <ovf:Property ovf:key="config-0004" ovf:type="string" \
ovf:userConfigurable="true" ovf:value="end" />
     </ovf:ProductSection>
""")

    def test_qualifiers_maxlen(self):
        """Ensure property values are limited by MaxLen qualifiers."""
        self.command.package = self.input_ovf
        vm = self.command.vm

        vm.set_property_value("login-password", "ababab")
        self.assertRaises(ValueUnsupportedError,
                          vm.set_property_value,
                          "login-password",
                          # max length 25 characters according to OVF
                          "abcdefghijklmnopqrstuvwxyz")

    def test_qualifiers_minlen(self):
        """Ensure property values are limited by MinLen qualifiers."""
        self.command.package = self.invalid_ovf
        self.assertLogged(**self.UNRECOGNIZED_PRODUCT_CLASS)
        self.assertLogged(**self.NONEXISTENT_FILE)
        vm = self.command.vm

        vm.set_property_value("jabberwock", "super duper alley-ooper scooper")
        self.assertRaises(ValueUnsupportedError,
                          vm.set_property_value,
                          "jabberwock",
                          "short")

    def test_update_label_and_description(self):
        """Update label and description for existing properties."""
        self.command.package = self.input_ovf
        self.command.properties = ["hostname", "enable-ssh-server"]
        self.command.labels = ["Hostname", "Enable Remote SSH Access"]
        self.command.descriptions = ["Enter the router hostname",
                                     "Enable <sshd>; disable <telnetd>"]
        self.command.run()
        self.command.finished()
        self.check_diff("""
       <ovf:Property ovf:key="hostname" ovf:qualifiers="MaxLen(63)" \
ovf:type="string" ovf:userConfigurable="true" ovf:value="">
-        <ovf:Label>Router Name</ovf:Label>
-        <ovf:Description>Hostname of this router</ovf:Description>
+        <ovf:Label>Hostname</ovf:Label>
+        <ovf:Description>Enter the router hostname</ovf:Description>
       </ovf:Property>
...
       <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" \
ovf:userConfigurable="true" ovf:value="false">
-        <ovf:Label>Enable SSH Login</ovf:Label>
-        <ovf:Description>Enable remote login via SSH and disable remote \
login via telnet. Requires login-username and login-password to be \
set!</ovf:Description>
+        <ovf:Label>Enable Remote SSH Access</ovf:Label>
+        <ovf:Description>Enable &lt;sshd&gt;; disable \
&lt;telnetd&gt;</ovf:Description>
       </ovf:Property>
""")

    def test_create_property_no_preexisting(self):
        """Set property values for an OVF that has none previously."""
        self.command.package = self.minimal_ovf
        self.command.properties = ["hello=world"]
        self.command.run()
        self.command.finished()
        self.check_diff(file1=self.minimal_ovf, expected="""
     </ovf:VirtualHardwareSection>
+    <ovf:ProductSection>
+      <ovf:Info>Product Information</ovf:Info>
+      <ovf:Property ovf:key="hello" ovf:type="string" ovf:value="world" />
+    </ovf:ProductSection>
   </ovf:VirtualSystem>
""")

    def test_create_property_no_preexisting_v09(self):
        """Set property for a v0.9 OVF with no pre-existing properties."""
        self.command.package = self.v09_ovf
        self.command.properties = ["hello=world"]
        self.assertRaises(NotImplementedError, self.command.run)

    def test_config_file_not_supported(self):
        """Platform doesn't support literal CLI configuration."""
        self.command.package = self.iosv_ovf
        self.command.config_file = self.sample_cfg
        self.assertRaises(NotImplementedError,
                          self.command.run)

    def test_set_transport(self):
        """Set environment transport value."""
        self.command.package = self.input_ovf
        self.command.transports = ['ibm', 'iso', 'vmware']
        self.assertEqual(self.command.transports,
                         ["http://www.ibm.com/xmlns/ovf/transport/filesystem/"
                          "etc/ovf-transport", "iso", "com.vmware.guestInfo"])
        self.command.run()
        self.command.finished()
        self.check_diff("""
     </ovf:OperatingSystemSection>
-    <ovf:VirtualHardwareSection ovf:transport="iso">
+    <ovf:VirtualHardwareSection ovf:transport="http://www.ibm.com/xmlns/ovf/\
transport/filesystem/etc/ovf-transport iso com.vmware.guestInfo">
       <ovf:Info>Virtual hardware requirements</ovf:Info>
""")

    UNKNOWN_TRANSPORT = {
        'levelname': 'WARNING',
        'msg': "Unknown transport value '%s'. .*",
        'args': ('foobar', ),
    }

    def test_set_transport_unknown(self):
        """Setting the transport to an unknown value is OK but warned about."""
        self.command.package = self.input_ovf
        self.command.transports = ['com.vmware.guestInfo', 'foobar']
        self.assertLogged(**self.UNKNOWN_TRANSPORT)
        self.assertEqual(self.command.transports,
                         ['com.vmware.guestInfo', 'foobar'])
        self.command.run()
        self.command.finished()
        self.check_diff("""
     </ovf:OperatingSystemSection>
-    <ovf:VirtualHardwareSection ovf:transport="iso">
+    <ovf:VirtualHardwareSection ovf:transport="com.vmware.guestInfo foobar">
       <ovf:Info>Virtual hardware requirements</ovf:Info>
""")

    def test_set_transport_v09(self):
        """Set the transport method for a v0.9 OVF."""
        self.command.package = self.v09_ovf
        self.command.transports = ['iso']
        self.assertRaises(NotImplementedError, self.command.run)

    def test_edit_interactive(self):
        """Exercise the interactive CLI for COT edit-properties."""
        menu_prompt = """
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

        username_edit_prompt = """
Key:            "login-username"
Label:          "Login Username"
Description:    "Username for remote login"
Type:           "string"
Qualifiers:     "MaxLen(64)"
Current Value:  ""

Enter new value for this property
        """.strip()

        ssh_edit_prompt = """
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

        # List of tuples:
        # (expected_prompt, input_to_provide, expected_log)
        prompt_idx = 0
        input_idx = 1
        msgs_idx = 2
        expected = [
            # select by name prefix
            (menu_prompt, "login-u", None),
            # unchanged value, return to menu
            (username_edit_prompt, "", {'levelname': 'INFO',
                                        'msg': 'Value.*unchanged', }),

            # select by number
            (menu_prompt, "1", None),
            # invalid value
            (username_edit_prompt,
             ("thisiswaytoolongofastringtouseforausername"
              "whatamipossiblythinking!"),
             {'levelname': 'ERROR',
              'msg': 'Unsupported value.*login-username.*64 characters', }),
            # valid value, update and return to menu
            (username_edit_prompt, "hello",
             {'levelname': 'INFO',
              'msg': 'Successfully updated property', }),

            # out of range menu selection
            (menu_prompt, "27",
             {'levelname': 'ERROR', 'msg': 'Invalid input', }),

            # select by number
            (menu_prompt, "1", None),
            # valid value, return to menu
            (re.sub('Value:  ""', 'Value:  "hello"', username_edit_prompt),
             "goodbye",
             {'levelname': 'INFO', 'msg': 'Successfully updated property', }),

            # ambiguous selection
            (menu_prompt, "enable-",
             {'levelname': 'ERROR', 'msg': 'Invalid input', }),

            # unambiguous selection
            (menu_prompt, "enable-ssh", None),
            # value to be munged, no change, return
            (ssh_edit_prompt, "n",
             {'levelname': 'INFO', 'msg': 'Successfully updated property', }),

            # unambiguous selection
            (menu_prompt, "enable-ssh", None),
            # not a valid boolean
            (ssh_edit_prompt, "nope",
             {'levelname': 'ERROR',
              'msg': 'Unsupported value.*enable-ssh-server.*boolean', }),
            # valid boolean, update and return to menu
            (ssh_edit_prompt, "true",
             {'levelname': 'INFO', 'msg': 'Successfully updated property', }),

            # done
            (menu_prompt, "q", None),
        ]

        def custom_input(prompt,
                         default_value):  # pylint: disable=unused-argument
            """Mock for :meth:`COT.ui.UI.get_input`.

            For the parameters, see get_input.
            """
            if self.counter > 0:
                log = expected[self.counter-1][msgs_idx]
                if log is not None:
                    self.assertLogged(info='After step {0}, '
                                      .format(self.counter - 1),
                                      **log)  # pylint: disable=not-a-mapping
                else:
                    self.assertNoLogsOver(logging.INFO,
                                          info='After step {0}, '
                                          .format(self.counter - 1))
            # Get output and flush it
            # Make sure it matches expectations
            self.maxDiff = None
            self.assertMultiLineEqual(
                expected[self.counter][prompt_idx], prompt,
                "failed at index {0}! Expected:\n{1}\nActual:\n{2}".format(
                    self.counter, expected[self.counter][prompt_idx], prompt))
            # Return our canned input
            canned_input = expected[self.counter][input_idx]
            self.counter += 1
            return canned_input

        _input = self.command.ui.get_input
        try:
            self.command.ui.get_input = custom_input
            self.command.package = self.input_ovf
            self.command.run()
            log = expected[self.counter - 1][msgs_idx]
            if log is not None:
                self.assertLogged(**log)  # pylint: disable=not-a-mapping
        finally:
            self.command.ui.get_input = _input
        self.command.finished()
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
