#!/usr/bin/env python
#
# test_info.py - Unit test cases for COTInfo class.
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

"""Unit test cases for the COT.info.COTInfo class."""

from COT.commands.tests.command_testcase import CommandTestCase
from COT.commands.info import COTInfo
from COT.data_validation import InvalidInputError


class TestCOTInfo(CommandTestCase):
    """Test cases for the COTInfo class."""

    command_class = COTInfo

    def test_readiness(self):
        """Test ready_to_run() under various combinations of parameters."""
        ready, reason = self.command.ready_to_run()
        self.assertFalse(ready)
        self.assertEqual("At least one package must be specified", reason)
        self.assertRaises(InvalidInputError, self.command.run)

        self.command.package_list = [self.input_ovf]
        ready, reason = self.command.ready_to_run()
        self.assertTrue(ready)

    def test_invalid_args(self):
        """Test various invalid inputs."""
        # pylint: disable=redefined-variable-type
        with self.assertRaises(InvalidInputError):
            self.command.package_list = ["/foo/bar/baz"]
        with self.assertRaises(InvalidInputError):
            self.command.verbosity = True
        with self.assertRaises(InvalidInputError):
            self.command.verbosity = 0

    def test_minimal_ovf(self):
        """Get info for minimal OVF with no real content."""
        # For an OVF this simple, standard/brief/verbose output are the same
        expected_output = """
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Configuration Profiles:  CPUs    Memory NICs Serials Disks/Capacity
                         ---- --------- ---- ------- --------------
  None (default)            0       0 B    0       0  0 /       0 B
""".format(self.minimal_ovf)
        self.command.package_list = [self.minimal_ovf]

        self.check_cot_output(expected_output)

        self.command.verbosity = 'brief'
        self.check_cot_output(expected_output)

        self.command.verbosity = 'verbose'
        self.check_cot_output(expected_output)

    def test_multiple_minimal_ovf(self):
        """Test handling for multiple OVFs at once."""
        self.command.package_list = [self.minimal_ovf, self.minimal_ovf]
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Configuration Profiles:  CPUs    Memory NICs Serials Disks/Capacity
                         ---- --------- ---- ------- --------------
  None (default)            0       0 B    0       0  0 /       0 B

-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Configuration Profiles:  CPUs    Memory NICs Serials Disks/Capacity
                         ---- --------- ---- ------- --------------
  None (default)            0       0 B    0       0  0 /       0 B
""".format(self.minimal_ovf))

    def test_input_ovf(self):
        """Test the standard input ovf."""
        self.command.package_list = [self.input_ovf]
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Product:  PRODUCT
          PRODUCT_URL
Vendor:   VENDOR
          VENDOR_URL
Version:  DEV
          DEVELOPMENT IMAGE

Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  input.vmdk           149 KiB     1 GiB harddisk @ SCSI 0:0
  input.iso            352 KiB           cdrom @ IDE 1:0
  sample_cfg.txt          78 B

Hardware Variants:
  System types:             vmx-07 vmx-08
  SCSI device types:        lsilogic
  Ethernet device types:    VMXNET3

Configuration Profiles:   CPUs    Memory NICs Serials Disks/Capacity
                          ---- --------- ---- ------- --------------
  4CPU-4GB-3NIC (default)    4     4 GiB    3       2  1 /     1 GiB
    Label:          "4 vCPUs, 4 GB RAM, 3 NICs"
    Description:    "Default hardware profile - 4 vCPUs, 4 GB RAM, 3 NICs"
  1CPU-1GB-1NIC              1     1 GiB    1       2  1 /     1 GiB
    Label:          "1 vCPU, 1 GB RAM, 1 NIC"
    Description:    "Minimal hardware profile - 1 vCPU, 1 GB RAM, 1 NIC"
  2CPU-2GB-1NIC              2     2 GiB    1       2  1 /     1 GiB
    Label:          "2 vCPUs, 2 GB RAM, 1 NIC"
    Description:    "Minimal hardware profile - 2 vCPUs, 2 GB RAM, 1 NIC"

Networks:
  VM Network  "VM Network"

NICs and Associated Networks:
  GigabitEthernet1 : VM Network
  GigabitEthernet2 : VM Network
  GigabitEthernet3 : VM Network

Environment:
  Transport types: iso

Properties:
  <login-username>       Login Username                   ""
  <login-password>       Login Password                   ""
  <mgmt-ipv4-addr>       Management IPv4 Address/Mask     ""
  <mgmt-ipv4-gateway>    Management IPv4 Default Gateway  ""
  <hostname>             Router Name                      ""
  <enable-ssh-server>    Enable SSH Login                 "false"
  <enable-http-server>   Enable HTTP Server               "false"
  <enable-https-server>  Enable HTTPS Server              "false"
  <privilege-password>   Enable Password                  ""
  <domain-name>          Domain Name                      ""
""".format(self.input_ovf))

        self.command.verbosity = 'brief'
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Product:  PRODUCT
Vendor:   VENDOR
Version:  DEV

Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  input.vmdk           149 KiB     1 GiB harddisk @ SCSI 0:0
  input.iso            352 KiB           cdrom @ IDE 1:0
  sample_cfg.txt          78 B

Hardware Variants:
  System types:             vmx-07 vmx-08
  SCSI device types:        lsilogic
  Ethernet device types:    VMXNET3

Configuration Profiles:   CPUs    Memory NICs Serials Disks/Capacity
                          ---- --------- ---- ------- --------------
  4CPU-4GB-3NIC (default)    4     4 GiB    3       2  1 /     1 GiB
  1CPU-1GB-1NIC              1     1 GiB    1       2  1 /     1 GiB
  2CPU-2GB-1NIC              2     2 GiB    1       2  1 /     1 GiB

Networks:
  VM Network  "VM Network"

Environment:
  Transport types: iso

Properties:
  <login-username>       Login Username                   ""
  <login-password>       Login Password                   ""
  <mgmt-ipv4-addr>       Management IPv4 Address/Mask     ""
  <mgmt-ipv4-gateway>    Management IPv4 Default Gateway  ""
  <hostname>             Router Name                      ""
  <enable-ssh-server>    Enable SSH Login                 "false"
  <enable-http-server>   Enable HTTP Server               "false"
  <enable-https-server>  Enable HTTPS Server              "false"
  <privilege-password>   Enable Password                  ""
  <domain-name>          Domain Name                      ""
""".format(self.input_ovf))

        self.command.verbosity = 'verbose'
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Product:  PRODUCT
          PRODUCT_URL
Vendor:   VENDOR
          VENDOR_URL
Version:  DEV
          DEVELOPMENT IMAGE

Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  input.vmdk           149 KiB     1 GiB harddisk @ SCSI 0:0
    File ID: file1
    Disk ID: vmdisk1
  input.iso            352 KiB           cdrom @ IDE 1:0
    File ID: file2
  sample_cfg.txt          78 B
    File ID: textfile

Hardware Variants:
  System types:             vmx-07 vmx-08
  SCSI device types:        lsilogic
  Ethernet device types:    VMXNET3

Configuration Profiles:   CPUs    Memory NICs Serials Disks/Capacity
                          ---- --------- ---- ------- --------------
  4CPU-4GB-3NIC (default)    4     4 GiB    3       2  1 /     1 GiB
    Label:          "4 vCPUs, 4 GB RAM, 3 NICs"
    Description:    "Default hardware profile - 4 vCPUs, 4 GB RAM, 3 NICs"
  1CPU-1GB-1NIC              1     1 GiB    1       2  1 /     1 GiB
    Label:          "1 vCPU, 1 GB RAM, 1 NIC"
    Description:    "Minimal hardware profile - 1 vCPU, 1 GB RAM, 1 NIC"
  2CPU-2GB-1NIC              2     2 GiB    1       2  1 /     1 GiB
    Label:          "2 vCPUs, 2 GB RAM, 1 NIC"
    Description:    "Minimal hardware profile - 2 vCPUs, 2 GB RAM, 1 NIC"

Networks:
  VM Network  "VM Network"

NICs and Associated Networks:
  GigabitEthernet1 : VM Network
    VMXNET3 ethernet adapter on "VM Network"
  GigabitEthernet2 : VM Network
    VMXNET3 ethernet adapter on "VM Network"
  GigabitEthernet3 : VM Network
    VMXNET3 ethernet adapter on "VM Network"

Environment:
  Transport types: iso

Properties:
  <login-username>       Login Username                   ""
      Username for remote login
  <login-password>       Login Password                   ""
      Password for remote login.
      WARNING: While this password will be stored securely within IOS, the
      plain-text password will be recoverable from the OVF descriptor file.
  <mgmt-ipv4-addr>       Management IPv4 Address/Mask     ""
      IPv4 address and mask for management interface (such as "10.1.1.100/24"
      or "10.1.1.100 255.255.255.0"), or "dhcp" to configure via DHCP
  <mgmt-ipv4-gateway>    Management IPv4 Default Gateway  ""
      IPv4 default gateway address (such as "10.1.1.1") for management
      interface, or "dhcp" to configure via DHCP
  <hostname>             Router Name                      ""
      Hostname of this router
  <enable-ssh-server>    Enable SSH Login                 "false"
      Enable remote login via SSH and disable remote login via telnet. Requires
      login-username and login-password to be set!
  <enable-http-server>   Enable HTTP Server               "false"
      Enable HTTP server capability for REST API
  <enable-https-server>  Enable HTTPS Server              "false"
      Enable HTTPS server capability for REST API
  <privilege-password>   Enable Password                  ""
      Password for privileged (enable) access.
      WARNING: While this password will be stored securely within IOS, the
      plain-text password will be recoverable from the OVF descriptor file.
  <domain-name>          Domain Name                      ""
      Network domain name (such as "cisco.com")
""".format(self.input_ovf))

    def test_iosv_ovf(self):
        """Test an IOSv OVF."""
        self.command.package_list = [self.iosv_ovf]

        self.command.verbosity = 'brief'
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
COT detected platform type: Cisco IOSv
-------------------------------------------------------------------------------
Product:  Cisco IOSv Virtual Router
Vendor:   Cisco Systems, Inc.
Version:  15.4(2.4)T

Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  input.vmdk           149 KiB     1 GiB harddisk @ IDE 0:0
  (disk placeholder)        --   128 MiB harddisk @ IDE 0:1

Hardware Variants:
  System types:             vmx-08 Cisco:Internal:VMCloud-01
  IDE device types:         virtio
  Ethernet device types:    E1000

Configuration Profiles:     CPUs    Memory NICs Serials Disks/Capacity
                            ---- --------- ---- ------- --------------
  1CPU-384MB-2NIC (default)    1   384 MiB    2       2  2 / 1.125 GiB
  1CPU-1GB-8NIC                1     1 GiB    8       2  2 / 1.125 GiB
  1CPU-3GB-10NIC               1     3 GiB   10       2  2 / 1.125 GiB
  1CPU-3GB-16NIC               1     3 GiB   16       2  2 / 1.125 GiB

Networks:
  GigabitEthernet0_0   "Data network 1"
  GigabitEthernet0_1   "Data network 2"
  GigabitEthernet0_2   "Data network 3"
  GigabitEthernet0_3   "Data network 4"
  GigabitEthernet0_4   "Data network 5"
  GigabitEthernet0_5   "Data network 6"
  GigabitEthernet0_6   "Data network 7"
  GigabitEthernet0_7   "Data network 8"
  GigabitEthernet0_8   "Data network 9"
  GigabitEthernet0_9   "Data network 10"
  GigabitEthernet0_10  "Data network 11"
  GigabitEthernet0_11  "Data network 12"
  GigabitEthernet0_12  "Data network 13"
  GigabitEthernet0_13  "Data network 14"
  GigabitEthernet0_14  "Data network 15"
  GigabitEthernet0_15  "Data network 16"
""".format(self.iosv_ovf))

        self.command.verbosity = 'verbose'
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
COT detected platform type: Cisco IOSv
-------------------------------------------------------------------------------
Product:  Cisco IOSv Virtual Router
          http://www.cisco.com/en/US/products/index.html
Vendor:   Cisco Systems, Inc.
          http://www.cisco.com
Version:  15.4(2.4)T
          Cisco IOS Software, IOSv Software (VIOS-ADVENTERPRISEK9-M), Version
          15.4(2.4)T,  ENGINEERING WEEKLY BUILD, synced to  V153_3_M1_9

Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  input.vmdk           149 KiB     1 GiB harddisk @ IDE 0:0
    File ID: vios-adventerprisek9-m.vmdk
    Disk ID: vios-adventerprisek9-m.vmdk
  (disk placeholder)        --   128 MiB harddisk @ IDE 0:1

Hardware Variants:
  System types:             vmx-08 Cisco:Internal:VMCloud-01
  IDE device types:         virtio
  Ethernet device types:    E1000

Configuration Profiles:     CPUs    Memory NICs Serials Disks/Capacity
                            ---- --------- ---- ------- --------------
  1CPU-384MB-2NIC (default)    1   384 MiB    2       2  2 / 1.125 GiB
    Label:          "Small"
    Description:    "Minimal hardware profile - 1 vCPU, 384 MB RAM, 2 NICs"
  1CPU-1GB-8NIC                1     1 GiB    8       2  2 / 1.125 GiB
    Label:          "Medium"
    Description:    "Medium hardware profile - 1 vCPU, 1 GB RAM, 8 NICs"
  1CPU-3GB-10NIC               1     3 GiB   10       2  2 / 1.125 GiB
    Label:          "Large (ESXi)"
    Description:    "Large hardware profile for ESXi - 1 vCPU, 3 GB RAM, 10
                     NICs"
  1CPU-3GB-16NIC               1     3 GiB   16       2  2 / 1.125 GiB
    Label:          "Large (non-ESXi)"
    Description:    "Large hardware profile for other hypervisors - 1 vCPU, 3
                     GB RAM, 16 NICs. (Note: ESXi only permits 10 NICs in a VM
                     so this profile is unsupported on ESXi.)"

Networks:
  GigabitEthernet0_0   "Data network 1"
  GigabitEthernet0_1   "Data network 2"
  GigabitEthernet0_2   "Data network 3"
  GigabitEthernet0_3   "Data network 4"
  GigabitEthernet0_4   "Data network 5"
  GigabitEthernet0_5   "Data network 6"
  GigabitEthernet0_6   "Data network 7"
  GigabitEthernet0_7   "Data network 8"
  GigabitEthernet0_8   "Data network 9"
  GigabitEthernet0_9   "Data network 10"
  GigabitEthernet0_10  "Data network 11"
  GigabitEthernet0_11  "Data network 12"
  GigabitEthernet0_12  "Data network 13"
  GigabitEthernet0_13  "Data network 14"
  GigabitEthernet0_14  "Data network 15"
  GigabitEthernet0_15  "Data network 16"

NICs and Associated Networks:
  GigabitEthernet0/0  : GigabitEthernet0_0
    NIC representing GigabitEthernet0/0 interface
  GigabitEthernet0/1  : GigabitEthernet0_1
    NIC representing GigabitEthernet0/1 interface
  GigabitEthernet0/2  : GigabitEthernet0_2
    NIC representing GigabitEthernet0/2 interface
  GigabitEthernet0/3  : GigabitEthernet0_3
    NIC representing GigabitEthernet0/3 interface
  GigabitEthernet0/4  : GigabitEthernet0_4
    NIC representing GigabitEthernet0/4 interface
  GigabitEthernet0/5  : GigabitEthernet0_5
    NIC representing GigabitEthernet0/5 interface
  GigabitEthernet0/6  : GigabitEthernet0_6
    NIC representing GigabitEthernet0/6 interface
  GigabitEthernet0/7  : GigabitEthernet0_7
    NIC representing GigabitEthernet0/7 interface
  GigabitEthernet0/8  : GigabitEthernet0_8
    NIC representing GigabitEthernet0/8 interface
  GigabitEthernet0/9  : GigabitEthernet0_9
    NIC representing GigabitEthernet0/9 interface
  GigabitEthernet0/10 : GigabitEthernet0_10
    NIC representing GigabitEthernet0/10 interface
  GigabitEthernet0/11 : GigabitEthernet0_11
    NIC representing GigabitEthernet0/11 interface
  GigabitEthernet0/12 : GigabitEthernet0_12
    NIC representing GigabitEthernet0/12 interface
  GigabitEthernet0/13 : GigabitEthernet0_13
    NIC representing GigabitEthernet0/13 interface
  GigabitEthernet0/14 : GigabitEthernet0_14
    NIC representing GigabitEthernet0/14 interface
  GigabitEthernet0/15 : GigabitEthernet0_15
    NIC representing GigabitEthernet0/15 interface
""".format(self.iosv_ovf))

    def test_v09_ovf(self):
        """Test a legacy v0.9 OVF."""
        self.command.package_list = [self.v09_ovf]
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Annotation: Hello world! This is a version 0.9 OVF.

            Are you still reading this?

End User License Agreement(s):
  Licensing agreement
    (not displayed, use 'cot info --verbose' if desired)

Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  input.vmdk           149 KiB     1 GiB harddisk @ SCSI 0:0

Hardware Variants:
  System types:             vmx-04
  SCSI device types:        lsilogic
  Ethernet device types:    PCNet32

Configuration Profiles:  CPUs    Memory NICs Serials Disks/Capacity
                         ---- --------- ---- ------- --------------
  None (default)            1     8 GiB    1       0  1 /     1 GiB

Networks:
  bridged  "The bridged network"

NICs and Associated Networks:
  ethernet0     : bridged
""".format(self.v09_ovf))

        self.command.verbosity = 'verbose'
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Annotation: Hello world! This is a version 0.9 OVF.

            Are you still reading this?

End User License Agreement(s):
  Licensing agreement
    Licensing text, oh licensing text!
    How lovely is thy legalese!

    1. Open Virtualization Format
    2. ????
    3. Profit!

Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  input.vmdk           149 KiB     1 GiB harddisk @ SCSI 0:0
    File ID: file1
    Disk ID: vmdisk1

Hardware Variants:
  System types:             vmx-04
  SCSI device types:        lsilogic
  Ethernet device types:    PCNet32

Configuration Profiles:  CPUs    Memory NICs Serials Disks/Capacity
                         ---- --------- ---- ------- --------------
  None (default)            1     8 GiB    1       0  1 /     1 GiB

Networks:
  bridged  "The bridged network"

NICs and Associated Networks:
  ethernet0     : bridged
    PCNet32 ethernet adapter
""".format(self.v09_ovf))

    def test_vmware_ovf(self):
        """Test info string for an OVF with VMware custom extensions."""
        self.command.package_list = [self.vmware_ovf]
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  input.vmdk           149 KiB     1 GiB harddisk @ SCSI 0:0

Hardware Variants:
  System types:             vmx-08
  SCSI device types:        virtio lsilogic
  Ethernet device types:    E1000

Configuration Profiles:  CPUs    Memory NICs Serials Disks/Capacity
                         ---- --------- ---- ------- --------------
  None (default)            2   1.5 GiB    4       0  1 /     1 GiB

Networks:
  lanethernet0  "The lanethernet0 network"

NICs and Associated Networks:
  Network adapter 1 : lanethernet0
  Network adapter 2 : lanethernet0
  Network adapter 3 : lanethernet0
  Network adapter 4 : lanethernet0

Properties:
  <custom-property>  "custom-value"
""".format(self.vmware_ovf))

        self.command.verbosity = 'verbose'
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  input.vmdk           149 KiB     1 GiB harddisk @ SCSI 0:0
    File ID: file1
    Disk ID: vmdisk1

Hardware Variants:
  System types:             vmx-08
  SCSI device types:        virtio lsilogic
  Ethernet device types:    E1000

Configuration Profiles:  CPUs    Memory NICs Serials Disks/Capacity
                         ---- --------- ---- ------- --------------
  None (default)            2   1.5 GiB    4       0  1 /     1 GiB

Networks:
  lanethernet0  "The lanethernet0 network"

NICs and Associated Networks:
  Network adapter 1 : lanethernet0
    E1000 ethernet adapter on "lanethernet0"
  Network adapter 2 : lanethernet0
    E1000 ethernet adapter on "lanethernet0"
  Network adapter 3 : lanethernet0
    E1000 ethernet adapter on "lanethernet0"
  Network adapter 4 : lanethernet0
    E1000 ethernet adapter on "lanethernet0"

Properties:
  <custom-property>  "custom-value"
""".format(self.vmware_ovf))

    def test_v20_vbox_ovf(self):
        """Test info string for v2.0 OVF generated by VirtualBox."""
        self.command.package_list = [self.v20_vbox_ovf]
        self.command.verbosity = "verbose"
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Files and Disks:        File Size  Capacity Device
                        --------- --------- --------------------
  ubuntu.2.0-disk1.vmdk               8 GiB harddisk @ SATA 0:0
    File ID: file1
    Disk ID: vmdisk1

Hardware Variants:
  System types:             virtualbox-2.2
  IDE device types:         PIIX4
  Ethernet device types:    E1000

Configuration Profiles:  CPUs    Memory NICs Serials Disks/Capacity
                         ---- --------- ---- ------- --------------
  None (default)            1   512 MiB    1       0  1 /     8 GiB

Networks:
  NAT  "Logical network used by this appliance."

NICs and Associated Networks:
  <instance 10> : NAT
    Ethernet adapter on 'NAT'
""".format(self.v20_vbox_ovf))

    def test_invalid_ovf(self):
        """Test info string for OVF with various invalid/atypical contents."""
        self.command.package_list = [self.invalid_ovf]
        self.command.verbosity = "brief"
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Files and Disks:                       File Size  Capacity Device
                                       --------- --------- --------------------
  this_is_a_really_long_filename_fo...   149 KiB     1 GiB 
  input.iso                              352 KiB           cdrom @ (?) ?:0
  (disk placeholder)                          --   128 MiB 

Configuration Profiles:             CPUs    Memory NICs Serials Disks/Capacity
                                    ---- --------- ---- ------- --------------
  myprofile (default)                  3       0 B    1       0  1 / 1.125 GiB
  howlongofaprofilenamecanweusehere    0       1 B    0       0  1 / 1.125 GiB

Networks:
  This is a rather verbose network name, eh what?  "Why yes, it is!"
  name-but-no-description

Environment:
  Transport types:
    http://www.ibm.com/xmlns/ovf/transport/filesystem/etc/ovf-transport iso
    com.vmware.guestInfo

Properties:
  Antidisestablishmentarianism       "supercalifragilisticexpialidocious"
  <frobozz-is-a-magic-word-I-think>  "xyzzy"
""".format(self.invalid_ovf))    # noqa - trailing whitespace above is expected
        self.assertLogged(**self.UNRECOGNIZED_PRODUCT_CLASS)
        self.assertLogged(**self.NONEXISTENT_FILE)

        self.command.verbosity = "verbose"
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Product:  (No product string)
          (No product URL)
Vendor:   (No vendor string)
          (No vendor URL)
Version:  (No version string)
          Full version string goes here

Files and Disks:                       File Size  Capacity Device
                                       --------- --------- --------------------
  this_is_a_really_long_filename_fo...   149 KiB     1 GiB 
    File ID: input.vmdk
    Disk ID: input.vmdk
  input.iso                              352 KiB           cdrom @ (?) ?:0
    File ID: input.iso
  (disk placeholder)                          --   128 MiB 

Configuration Profiles:             CPUs    Memory NICs Serials Disks/Capacity
                                    ---- --------- ---- ------- --------------
  myprofile (default)                  3       0 B    1       0  1 / 1.125 GiB
    Label:          "what a profile"
    Description:    "this is"
  howlongofaprofilenamecanweusehere    0       1 B    0       0  1 / 1.125 GiB
    Label:          "howlongofaprofilenamecanweusehere"
    Description:    "prettylongitappears"

Networks:
  This is a rather verbose network name, eh what?  "Why yes, it is!"
  name-but-no-description

NICs and Associated Networks:
  <instance 27> : This is a rather verbose network name, eh what?

Environment:
  Transport types:
    http://www.ibm.com/xmlns/ovf/transport/filesystem/etc/ovf-transport iso
    com.vmware.guestInfo

Properties:
  Antidisestablishmentarianism       "supercalifragilisticexpialidocious"
      Anti-
      dis-
      establishment-
      arian-

      ...

      ism!
  <frobozz-is-a-magic-word-I-think>  "xyzzy"
""".format(self.invalid_ovf))    # noqa - trailing whitespace above is expected
        self.assertLogged(**self.UNRECOGNIZED_PRODUCT_CLASS)
        self.assertLogged(**self.NONEXISTENT_FILE)

    def test_wrapping(self):
        """Test info string on a narrower-than-usual terminal."""
        # pylint: disable=protected-access
        self.command.ui._terminal_width = 60

        self.command.package_list = [self.invalid_ovf]
        self.check_cot_output("""
-----------------------------------------------------------
{0}
-----------------------------------------------------------
Product:  (No product string)
          (No product URL)
Vendor:   (No vendor string)
          (No vendor URL)
Version:  (No version string)
          Full version string goes here

Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  this_is_a_reall...   149 KiB     1 GiB 
  input.iso            352 KiB           cdrom @ (?) ?:0
  (disk placeholder)        --   128 MiB 

Configuration Profiles:             CPUs    Memory NICs Serials Disks/Capacity
                                    ---- --------- ---- ------- --------------
  myprofile (default)                  3       0 B    1       0  1 / 1.125 GiB
    Label:          "what a profile"
    Description:    "this is"
  howlongofaprofilenamecanweusehere    0       1 B    0       0  1 / 1.125 GiB
    Label:          "howlongofaprofilenamecanweusehere"
    Description:    "prettylongitappears"

Networks:
  This is a rather verbose network name, eh what?  "Why..."
  name-but-no-description

NICs and Associated Networks:
  <instance 27> : This is a rather verbose network name, eh what?

Environment:
  Transport types:
    http://www.ibm.com/xmlns/ovf/transport/filesystem/etc/ovf-transport
    iso com.vmware.guestInfo

Properties:
  Antidisestablishmentarianism       "supercalifragilisticexpialidocious"
  <frobozz-is-a-magic-word-I-think>  "xyzzy"
""".format(self.invalid_ovf))    # noqa - trailing whitespace above is expected
        self.assertLogged(**self.UNRECOGNIZED_PRODUCT_CLASS)
        self.assertLogged(**self.NONEXISTENT_FILE)

        self.command.verbosity = "verbose"
        self.check_cot_output("""
-----------------------------------------------------------
{0}
-----------------------------------------------------------
Product:  (No product string)
          (No product URL)
Vendor:   (No vendor string)
          (No vendor URL)
Version:  (No version string)
          Full version string goes here

Files and Disks:     File Size  Capacity Device
                     --------- --------- --------------------
  this_is_a_reall...   149 KiB     1 GiB 
    File ID: input.vmdk
    Disk ID: input.vmdk
  input.iso            352 KiB           cdrom @ (?) ?:0
    File ID: input.iso
  (disk placeholder)        --   128 MiB 

Configuration Profiles:             CPUs    Memory NICs Serials Disks/Capacity
                                    ---- --------- ---- ------- --------------
  myprofile (default)                  3       0 B    1       0  1 / 1.125 GiB
    Label:          "what a profile"
    Description:    "this is"
  howlongofaprofilenamecanweusehere    0       1 B    0       0  1 / 1.125 GiB
    Label:          "howlongofaprofilenamecanweusehere"
    Description:    "prettylongitappears"

Networks:
  This is a rather verbose network name, eh what?  "Why
                                                    yes, it
                                                    is!"
  name-but-no-description

NICs and Associated Networks:
  <instance 27> : This is a rather verbose network name, eh what?

Environment:
  Transport types:
    http://www.ibm.com/xmlns/ovf/transport/filesystem/etc/ovf-transport
    iso com.vmware.guestInfo

Properties:
  Antidisestablishmentarianism       "supercalifragilisticexpialidocious"
      Anti-
      dis-
      establishment-
      arian-

      ...

      ism!
  <frobozz-is-a-magic-word-I-think>  "xyzzy"
""".format(self.invalid_ovf))    # noqa - trailing whitespace above is expected
        self.assertLogged(**self.UNRECOGNIZED_PRODUCT_CLASS)
        self.assertLogged(**self.NONEXISTENT_FILE)

    def test_ovf_failure(self):
        """Ensure info gracefully handles failure to load an OVF."""
        self.command.package_list = [self.ersatz_v3_ovf, self.minimal_ovf]
        # COT should report error in the first OVF but still show the second
        self.check_cot_output("""
-------------------------------------------------------------------------------
{0}
-------------------------------------------------------------------------------
Configuration Profiles:  CPUs    Memory NICs Serials Disks/Capacity
                         ---- --------- ---- ------- --------------
  None (default)            0       0 B    0       0  0 /       0 B
""".format(self.minimal_ovf))

        self.assertLogged(levelname="ERROR",
                          msg="Unable to display information for",
                          args=(self.ersatz_v3_ovf, ".*"))
