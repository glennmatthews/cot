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
* Deploy an OVF/OVA to an ESXi (VMware vSphere or vCenter) server to provision
  a new virtual machine (VM).

Examples
--------

Displaying a summary of OVA contents:

::

    > cot info --brief iosxrv.5.1.1.ova
    ---------------------------------------------------------------------------
    iosxrv.5.1.1.ova
    COT detected platform type: Cisco IOS XRv
    ---------------------------------------------------------------------------
    Product:  Cisco IOS XRv
    Vendor:   Cisco Systems, Inc.
    Version:  5.1.1

    Files and Disks:     File Size  Capacity Device
                         --------- --------- --------------------
      iosxrv.vmdk        271.59 MB   3.00 GB harddisk @ IDE 0:0

    Hardware Variants:
      System types:             vmx-08 Cisco:Internal:VMCloud-01
      Ethernet device types:    E1000

    Configuration Profiles:   CPUs    Memory NICs Serials Disks/Capacity
                              ---- --------- ---- ------- --------------
      1CPU-3GB-2NIC (default)    1   3.00 GB    2       2  1 /   3.00 GB
      2CPU-4GB-8NIC              2   4.00 GB    8       2  1 /   3.00 GB
      4CPU-6GB-10NIC             4   6.00 GB   10       2  1 /   3.00 GB


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
