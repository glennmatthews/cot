Introduction
============

.. raw:: html

   <p style="height:22px">
   <a href="https://pypi.python.org/pypi/cot/">
   <img src="https://img.shields.io/pypi/v/cot.svg"
        alt="Latest Version">
   </a>
   <a href="https://pypi.python.org/pypi/cot/">
   <img src="https://img.shields.io/badge/license-MIT-blue.svg"
        alt="License">
   </a>
   <a href="https://travis-ci.org/glennmatthews/cot">
   <img src="https://travis-ci.org/glennmatthews/cot.svg?branch=master"
        alt="Build Status">
   </a>
   <a href="https://coveralls.io/r/glennmatthews/cot?branch=master">
   <img
    src="https://coveralls.io/repos/glennmatthews/cot/badge.svg?branch=master"
    alt="Coverage Status">
   </a>
   <a href="https://readthedocs.org/projects/cot/?badge=latest">
   <img src="https://readthedocs.org/projects/cot/badge/?version=latest"
        alt="Documentation Status">
   </a>
   </p>

COT (the Common OVF Tool) is a tool for editing `Open Virtualization Format`_
(``.ovf``, ``.ova``) virtual appliances, with a focus on virtualized network
appliances such as the `Cisco CSR 1000V`_ and `Cisco IOS XRv`_ platforms.

COT's capabilities include:

* Add a disk or other file to an OVF/OVA
* Edit OVF hardware information (CPUs, RAM, NICs, configuration profiles, etc.)
* Edit product description information in an OVF/OVA
* Edit OVF environment properties
* Display a descriptive summary of the contents of an OVA or OVF package
* Embed a bootstrap configuration text file into an OVF/OVA.
* Remove files and disks from an OVF or OVA package
* Deploy an OVF/OVA to an ESXi (VMware vSphere or vCenter) server to provision
  a new virtual machine (VM).

Examples
--------

Displaying a summary of OVA contents:

::

    > cot info --brief csr1000v-universalk9.03.17.01.S.156-1.S1-std.ova
    -------------------------------------------------------------------------
    csr1000v-universalk9.03.17.01.S.156-1.S1-std.ova
    COT detected platform type: Cisco CSR1000V
    -------------------------------------------------------------------------
    Product:  Cisco CSR 1000V Cloud Services Router
    Vendor:   Cisco Systems, Inc.
    Version:  03.17.01.S.156-1.S1-std

    Files and Disks:                 File Size  Capacity Device
                                     --------- --------- --------------------
      csr1000v_harddisk.vmdk          71.5 KiB     8 GiB harddisk @ SCSI 0:0
      bdeo.sh                        52.42 KiB
      README-OVF.txt                 8.534 KiB
      README-BDEO.txt                6.748 KiB
      cot.tgz                        116.8 KiB
      csr1000v-universalk9.03.17....   425 MiB           cdrom @ IDE 1:0

    Hardware Variants:
      System types:             vmx-08 vmx-09 vmx-10 vmx-11
                                Cisco:Internal:VMCloud-01
      SCSI device types:        virtio lsilogic
      Ethernet device types:    VMXNET3 virtio

    Configuration Profiles:  CPUs    Memory NICs Serials Disks/Capacity
                             ---- --------- ---- ------- --------------
      1CPU-4GB (default)        1     4 GiB    3       2  1 /     8 GiB
      2CPU-4GB                  2     4 GiB    3       2  1 /     8 GiB
      4CPU-4GB                  4     4 GiB    3       2  1 /     8 GiB
      4CPU-8GB                  4     8 GiB    3       2  1 /     8 GiB

    Networks:
      GigabitEthernet1  "Data network 1"
      GigabitEthernet2  "Data network 2"
      GigabitEthernet3  "Data network 3"

    Environment:
      Transport types: iso

    Properties:
      <config-version>                                        "1.0"
      Router Name                                             ""
      Login Username                                          ""
      Login Password                                          ""
      Management Interface                                    "GigabitEthernet1"
      Management VLAN                                         ""
      Management Interface IPv4 Address/Mask                  ""
      Management IPv4 Gateway                                 ""
      Management IPv4 Network                                 ""
      PNSC IPv4 Address                                       ""
      PNSC Agent Local Port                                   ""
      PNSC Shared Secret Key                                  ""
      Remote Management IPv4 Address (optional, deprecated)   ""
      Enable SCP Server                                       "false"
      Enable SSH Login and Disable Telnet Login               "false"
      Enable Password                                         ""
      Domain Name                                             ""
      License boot level                                      "ax"
      Console                                                 ""
      Resource template                                       "default"
      Intercloud Mode                                         ""
      Intercloud Mode Management Key                          ""
      Intercloud Control Port                                 ""
      Intercloud Tunnel Port                                  ""
      Intercloud Tunnel Header Size                           "148"
      Intercloud Tunnel Interface IPv4 Address                ""
      Intercloud Tunnel Interface Gateway IPv4 Address        ""

Adding a custom hardware configuration profile to an OVA:

::

    > cot edit-hardware csr1000v.ova --output csr1000v_custom.ova \
          --profile 1CPU-4GB --cpus 1 --memory 4GB

Customizing OVF environment properties:

::

    > cot edit-properties csr1000v.ova --output csr1000v_custom.ova \
          --properties mgmt-ipv4-addr=10.1.1.100/24 \
                       mgmt-ipv4-gateway=10.1.1.1


.. _`Open Virtualization Format`: http://dmtf.org/standards/ovf
.. _`Cisco CSR 1000V`: http://www.cisco.com/go/csr1000v
.. _`Cisco IOS XRv`: http://www.cisco.com/go/iosxrv
