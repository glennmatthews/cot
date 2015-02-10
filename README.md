Common OVF Tool (COT)
=====================

[![build status](https://api.travis-ci.org/glennmatthews/cot.svg?branch=develop)](https://travis-ci.org/glennmatthews/cot) [![Coverage Status](https://coveralls.io/repos/glennmatthews/cot/badge.svg?branch=develop)](https://coveralls.io/r/glennmatthews/cot?branch=develop)

COT (the Common OVF Tool) is a tool for editing
[Open Virtualization Format](http://dmtf.org/standards/ovf)
(`.ovf`, `.ova`) virtual appliances, with a focus on virtualized network
appliances such as the [Cisco CSR 1000V](http://www.cisco.com/go/csr1000v)
and [Cisco IOS XRv](http://www.cisco.com/go/iosxrv) platforms.

Table of Contents
=================

* [Capabilities](#capabilities)
* [System Requirements](#system-requirements)
* [Installation](#installation)
* [Examples](#examples)
* [Detailed Usage](#detailed-usage)
  * [`cot add-disk`](#cot-add-disk)
  * [`cot add-file`](#cot-add-file)
  * [`cot deploy`](#cot-deploy)
    * [`cot deploy esxi`](#cot-deploy-esxi)
  * [`cot edit-hardware`](#cot-edit-hardware)
  * [`cot edit-product`](#cot-edit-product)
  * [`cot edit-properties`](#cot-edit-properties)
  * [`cot info`](#cot-info)
  * [`cot inject-config`](#cot-inject-config)

Capabilities
============

COT's capabilities include:

* Add a disk or other file to an OVF/OVA
* Edit OVF hardware information (CPUs, RAM, NICs, configuration profiles, etc.)
* Edit product description information in an OVF/OVA
* Edit OVF environment properties
* Display a descriptive summary of the contents of an OVA or OVF package
* Embed a bootstrap configuration text file into an OVF/OVA.
* Deploy an OVF/OVA to an ESXi (VMware vSphere or vCenter) server to provision
  a new virtual machine (VM).

System Requirements
===================

* COT is supported under Mac OS X and Ubuntu at present and requires either
  Python 2.7 or Python 3.2 or later.
* COT now has limited support for CentOS and Python 2.6 as well.
* COT uses [`qemu-img`](http://www.qemu.org) as a helper program for various
  operations involving the creation, inspection, and modification of
  hard disk image files packaged in an OVF.
* The `cot add-disk` command requires either `qemu-img` (version 2.1 or later)
  or [`vmdktool`](http://www.freshports.org/sysutils/vmdktool/) as a
  helper program when adding hard disks to an OVF.
* The `cot inject-config` command requires
  [`mkisofs`](http://cdrecord.org/) to create ISO
  (CD-ROM) images and/or [`fatdisk`](http://github.com/goblinhack/fatdisk)
  to create hard disk images.
* The `cot deploy ... esxi` command requires
  [`ovftool`](https://www.vmware.com/support/developer/ovf/) to communicate
  with an ESXi server. If `ovftool` is installed, COT's automated unit tests
  will also make use of `ovftool` to perform additional verification that
  OVFs and OVAs created by COT align with VMware's expectations for these
  file types.


Installation
============

Refer to the included
[INSTALL.md](INSTALL.md)
for installation instructions, including how to download COT to your system.

Examples
========

Displaying a summary of OVA contents:

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
      4CPU-6GB-16NIC             4   6.00 GB   16       2  1 /   3.00 GB
      8CPU-8GB-10NIC             8   8.00 GB   10       2  1 /   3.00 GB
      8CPU-8GB-32NIC             8   8.00 GB   32       2  1 /   3.00 GB


Adding a custom hardware configuration profile to an OVA:

    > cot edit-hardware csr1000v.ova --output csr1000v_custom.ova \
          --profile 1CPU-4GB --cpus 1 --memory 4GB


Interactively customizing environment settings in an OVA:

    > cot edit-properties COT/tests/input.ovf --output output.ovf

    Please choose a property to edit:
       1) "Login Username"                         (login-username)
       2) "Login Password"                         (login-password)
       3) "Management IPv4 Address/Mask"           (mgmt-ipv4-addr)
       4) "Management IPv4 Default Gateway"        (mgmt-ipv4-gateway)
       5) "Router Name"                            (hostname)
       6) "Enable SSH Login"                       (enable-ssh-server)
       7) "Enable HTTP Server"                     (enable-http-server)
       8) "Enable HTTPS Server"                    (enable-https-server)
       9) "Enable Password"                        (privilege-password)
      10) "Domain Name"                            (domain-name)
    Enter property number to edit, or "q" to quit and write changes [q] 3

    Key:            "mgmt-ipv4-addr"
    Label:          "Management IPv4 Address/Mask"
    Description:    "IPv4 address and mask for management interface (such
                     as "10.1.1.100/24" or "10.1.1.100 255.255.255.0"), or
                     "dhcp" to configure via DHCP"
    Type:           "string"
    Qualifiers:     "MaxLen(33)"
    Current Value:  ""

    New value for this property [] 10.1.1.100/24
    Successfully set the value of property "mgmt-ipv4-addr" to "10.1.1.100/24" 

    Please choose a property to edit:
       1) "Login Username"                         (login-username)
       2) "Login Password"                         (login-password)
       3) "Management IPv4 Address/Mask"           (mgmt-ipv4-addr)
       4) "Management IPv4 Default Gateway"        (mgmt-ipv4-gateway)
       5) "Router Name"                            (hostname)
       6) "Enable SSH Login"                       (enable-ssh-server)
       7) "Enable HTTP Server"                     (enable-http-server)
       8) "Enable HTTPS Server"                    (enable-https-server)
       9) "Enable Password"                        (privilege-password)
      10) "Domain Name"                            (domain-name)
    Enter property number to edit, or "q" to quit and write changes [q] q


Non-interactively customizing environment properties:

    > cot edit-properties COT/tests/input.ovf --output output.ovf \
          --properties mgmt-ipv4-addr=10.1.1.100/24 \
                       mgmt-ipv4-gateway=10.1.1.1


Detailed Usage
==============

You can always get detailed help for COT by running `cot --help` or
`cot <command> --help`.

    > cot --help
    usage:
      cot --help
      cot --version
      cot help <command>
      cot <command> --help
      cot <options> <command> <command-options>

    Common OVF Tool (COT), version 1.2.1
    Copyright (C) 2013-2015 the COT project developers.
    A tool for editing Open Virtualization Format (.ovf, .ova) virtual
    appliances, with a focus on virtualized network appliances such as the
    Cisco CSR 1000V and Cisco IOS XRv platforms.

    optional arguments:
      -h, --help        show this help message and exit
      -V, --version     show program's version number and exit
      -f, --force       Perform requested actions without prompting for
                        confirmation
      -q, --quiet       Quiet output and logging (warnings and errors only)
      -v, --verbose     Verbose output and logging
      -vv, -d, --debug  Debug (most verbose) output and logging

    commands:
      <command>
        add-disk        Add a disk image to an OVF package and map it as a
                        disk in the guest environment
        add-file        Add a file to an OVF package
        deploy          Create a new VM on the target hypervisor from the
                        given OVF
        edit-hardware   Edit virtual machine hardware properties of an OVF
        edit-product    Edit product info in an OVF
        edit-properties
                        Edit environment properties of an OVF
        info            Generate a description of an OVF package
        inject-config   Inject a configuration file into an OVF package
        help            Print help for a command

    Note: some subcommands rely on external software tools, including:
    * qemu-img (http://www.qemu.org/)
    * mkisofs  (http://cdrecord.org/)
    * ovftool  (https://www.vmware.com/support/developer/ovf/)
    * fatdisk  (http://github.com/goblinhack/fatdisk)
    * vmdktool (http://www.freshports.org/sysutils/vmdktool/)

`cot add-disk`
--------------

    > cot add-disk --help
    usage:
      cot add-disk --help
      cot <opts> add-disk DISK_IMAGE PACKAGE [-o OUTPUT] [-f FILE_ID]
                          [-t {harddisk,cdrom}] [-c {ide,scsi}] [-s SUBTYPE]
                          [-a ADDRESS] [-d DESCRIPTION] [-n DISKNAME]

    Add or replace a disk image in the specified OVF or OVA. If the specified
    disk image, controller/address, file-id, and/or instance match an existing
    entry in the OVF, will replace the existing disk with the provided file
    (prompting for confirmation if --force was not set); otherwise, will
    create a new disk entry.

    positional arguments:
      DISK_IMAGE            Disk image file to add to the package
      PACKAGE               OVF descriptor or OVA file to edit

    general options:
      -h, --help            Show this help message and exit
      -o OUTPUT, --output OUTPUT
                            Name/path of new OVF/OVA package to create instead
                            of updating the existing OVF

    disk-related options:
      -f FILE_ID, --file-id FILE_ID
                            Disk image file ID string within the OVF package
                            (default: use disk image filename)
      -t {harddisk,cdrom}, --type {harddisk,cdrom}
                            Disk type (default: files ending in
                            .vmdk/.raw/.qcow2/.img will use harddisk and files
                            ending in .iso will use cdrom)

    controller-related options:
      -c {ide,scsi}, --controller {ide,scsi}
                            Disk controller type (default: determined by disk
                            type and platform)
      -a ADDRESS, --address ADDRESS
                            Address of the disk, such as "1:0". Requires that
                            --controller be explicitly set. (default: use
                            first unused address on the controller)
      -s SUBTYPE, --subtype SUBTYPE
                            Disk controller subtype such as "virtio" or
                            "lsilogic".

    descriptive options:
      -d DESCRIPTION, --description DESCRIPTION
                            Description of this disk (optional)
      -n DISKNAME, --name DISKNAME
                            Name of this disk (default: "Hard disk #" or "CD-
                            ROM #" as appropriate)

`cot add-file`
--------------

    > cot add-file --help
    usage:
      cot add-file --help
      cot <opts> add-file FILE PACKAGE [-o OUTPUT] [-f FILE_ID]

    Add or replace a file in the given OVF. If the specified file and/or file-
    id match existing package contents, will replace it (prompting for
    confirmation if --force was not set); otherwise, will create a new file
    entry.

    positional arguments:
      FILE                  File to add to the package
      PACKAGE               Package, OVF descriptor or OVA file to edit

    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUT, --output OUTPUT
                            Name/path of new VM package to create instead of
                            updating the existing package
      -f FILE_ID, --file-id FILE_ID
                            File ID string within the package (default: same
                            as filename)

`cot deploy`
------------

    > cot deploy --help
    usage:
      cot deploy --help
      cot <opts> deploy PACKAGE esxi ...

    Deploy a virtual machine to a specified server.

    positional arguments:
      PACKAGE               OVF descriptor or OVA file
      hypervisors supported:
        esxi                Deploy to ESXi, vSphere, or vCenter

    optional arguments:
      -h, --help            show this help message and exit

### `cot deploy esxi` ###

    > cot deploy PACKAGE esxi --help
    usage:
      cot deploy PACKAGE esxi --help
      cot <opts> deploy PACKAGE esxi LOCATOR [-u USERNAME] [-p PASSWORD]
                                     [-c CONFIGURATION] [-n VM_NAME] [-P]
                                     [-N OVF1=HOST1 [-N OVF2=HOST2 ...]]
                                     [-d DATASTORE] [-o=OVFTOOL_ARGS]

    Deploy OVF/OVA to ESXi/vCenter/vSphere hypervisor

    positional arguments:
      LOCATOR               vSphere target locator. Examples: "192.0.2.100"
                            (deploy directly to ESXi server),
                            "192.0.2.101/mydatacenter/host/192.0.2.100"
                            (deploy via vCenter server)

    optional arguments:
      -h, --help            show this help message and exit
      -u USERNAME, --username USERNAME
                            Server login username
      -p PASSWORD, --password PASSWORD
                            Server login password
      -c CONFIGURATION, --configuration CONFIGURATION
                            Use the specified configuration profile defined in
                            the OVF. If unspecified and the OVF has multiple
                            profiles, the user will be prompted or the default
                            configuration will be used.
      -n VM_NAME, --vm-name VM_NAME
                            Name to use for the VM (if applicable) and any
                            files created. If unspecified, the name of the OVF
                            will be used.
      -P, --power-on        Power on the created VM to begin booting
                            immediately.
      -N OVF_NET1=HOST_NET1 [OVF_NET2=HOST_NET2 ...]
                            Map networks named in the OVF to networks
                            (bridges, vSwitches, etc.) in the hypervisor
                            environment. This argument may be repeated as
                            needed to specify multiple mappings.
      -d DATASTORE, -ds DATASTORE, --datastore DATASTORE
                            ESXi datastore to use for the new VM
      -o OVFTOOL_ARGS, --ovftool-args OVFTOOL_ARGS
                            Quoted string describing additional CLI parameters
                            to pass through to "ovftool". Examples:
                            -o="--foo", --ovftool-args="--foo --bar"

    Examples:
      cot deploy foo.ova esxi 192.0.2.100 -u admin -p admin -n test_vm
        Deploy to vSphere/ESXi server 192.0.2.100 with credentials admin/admin,
        creating a VM named 'test_vm' from foo.ova.

      cot deploy foo.ova esxi 192.0.2.100 -u admin -c 1CPU-2.5GB
        Deploy to vSphere/ESXi server 192.0.2.100, with username admin
        (prompting the user to input a password at runtime), creating a VM
        based on profile '1CPU-2.5GB' in foo.ova.

      cot deploy foo.ova esxi "192.0.2.100/mydc/host/192.0.2.1" \
            -u administrator -N "GigabitEthernet1=VM Network" \
            -N "GigabitEthernet2=myvswitch"
        Deploy to vSphere server 192.0.2.1 which belongs to datacenter 'mydc'
        on vCenter server 192.0.2.100, and map the two NIC networks to
        vSwitches. Note that in this case -u specifies the vCenter login
        username.

      cot deploy foo.ova esxi 192.0.2.100 -u admin -p password \
            --ovftool-args="--overwrite --acceptAllEulas"
        Deploy with passthrough arguments to ovftool.


`cot edit-hardware`
-------------------

    > cot edit-hardware --help
    usage:
      cot edit-hardware --help
      cot <opts> edit-hardware PACKAGE [-o OUTPUT] -v TYPE [TYPE2 ...]
      cot <opts> edit-hardware PACKAGE [-o OUTPUT] [-p PROFILE [PROFILE2 ...]]
                               [-c CPUS] [-m MEMORY] [-n NICS]
                               [--nic-type {e1000,virtio,vmxnet3}]
                               [-N NETWORK [NETWORK2 ...]] [-M MAC1 [MAC2 ...]]
                               [--nic-names NAME1 [NAME2 ...]] [-s SERIAL_PORTS]
                               [-S URI1 [URI2 ...]]
                               [--scsi-subtype SCSI_SUBTYPE]
                               [--ide-subtype IDE_SUBTYPE]

    Edit hardware properties of the specified OVF or OVA

    positional arguments:
      PACKAGE               OVF descriptor or OVA file to edit

    general options:
      -h, --help            Show this help message and exit
      -o OUTPUT, --output OUTPUT
                            Name/path of new OVF/OVA package to create instead
                            of updating the existing OVF
      -v TYPE [TYPE2 ...], --virtual-system-type TYPE [TYPE2 ...]
                            Change virtual system type(s) supported by this
                            OVF/OVA package.
      -p PROFILE [PROFILE2 ...], --profiles PROFILE [PROFILE2 ...]
                            Make hardware changes only under the given
                            configuration profile(s). (default: changes apply
                            to all profiles)

    computational hardware options:
      -c CPUS, --cpus CPUS  Set the number of CPUs.
      -m MEMORY, --memory MEMORY
                            Set the amount of RAM. (Examples: "4096MB", "4GB")

    network interface options:
      -n NICS, --nics NICS  Set the number of NICs.
      --nic-type {e1000,virtio,vmxnet3}
                            Set the hardware type for all NICs. (default: do
                            not change existing NICs, and new NICs added will
                            match the existing type.)
      -N NETWORK [NETWORK2 ...], --nic-networks NETWORK [NETWORK2 ...]
                            Specify a series of one or more network names to
                            map NICs to. If N network names are specified, the
                            first (N-1) NICs will be mapped to the first (N-1)
                            networks and all remaining NICs will be mapped to
                            the Nth network.
      -M MAC1 [MAC2 ...], --mac-addresses-list MAC1 [MAC2 ...]
                            Specify a list of MAC addresses for the NICs. If N
                            MACs are specified, the first (N-1) NICs will
                            receive the first (N-1) MACs, and all remaining
                            NICs will receive the Nth MAC
      --nic-names NAME1 [NAME2 ...]
                            Specify a list of one or more NIC names or
                            patterns to apply to NIC devices. If N
                            names/patterns are specified, the first (N-1) NICs
                            will receive the first (N-1) names and remaining
                            NICs will be named based on the name or pattern of
                            the Nth item. See examples.

    serial port options:
      -s SERIAL_PORTS, --serial-ports SERIAL_PORTS
                            Set the number of serial ports.
      -S URI1 [URI2 ...], --serial-connectivity URI1 [URI2 ...]
                            Specify a series of connectivity strings (URIs
                            such as "telnet://localhost:9101") to map serial
                            ports to. If fewer URIs than serial ports are
                            specified, the remaining ports will be unmapped.

    disk and disk controller options:
      --scsi-subtype SCSI_SUBTYPE
                            Set resource subtype (such as "lsilogic" or
                            "virtio") for all SCSI controllers. If an empty
                            string is provided, any existing subtype will be
                            removed.
      --ide-subtype IDE_SUBTYPE
                            Set resource subtype (such as "virtio") for all
                            IDE controllers. If an empty string is provided,
                            any existing subtype will be removed.

    Examples:
      cot edit-hardware csr1000v.ova --output csr1000v_custom.ova \
            --profile 1CPU-4GB --cpus 1 --memory 8GB
        Create a new profile named "1CPU-8GB" with 1 CPU and 8 gigabytes of RAM

      cot edit-hardware input.ova -o output.ova --nic-names "mgmt" "eth{0}"
        Rename the NICs in the output OVA as 'mgmt', 'eth0', 'eth1', 'eth2'...

      cot edit-hardware input.ova -o output.ova --nic-names "Ethernet0/{10}"
        Rename the NICs in the output OVA as 'Ethernet0/10', 'Ethernet0/11',
        'Ethernet0/12', etc.


`cot edit-product`
------------------

    > cot edit-product --help
    usage:
      cot edit-product --help
      cot <opts> edit-product PACKAGE [-o OUTPUT] [-v SHORT_VERSION]
                              [-V FULL_VERSION]

    Edit product information attributes of the given OVF or OVA

    positional arguments:
      PACKAGE               OVF descriptor or OVA file to edit

    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUT, --output OUTPUT
                            Name/path of new OVF/OVA package to create instead
                            of updating the existing OVF
      -v SHORT_VERSION, --version SHORT_VERSION
                            Software short version string, such as "15.3(4)S"
                            or "5.2.0.01I"
      -V FULL_VERSION, --full-version FULL_VERSION
                            Software long version string, such as "Cisco IOS-
                            XE Software, Version 15.3(4)S"

`cot edit-properties`
---------------------

    > cot edit-properties --help
    usage:
      cot edit-properties --help
      cot <opts> edit-properties PACKAGE -p KEY1=VALUE1 [KEY2=VALUE2 ...]
                                 [-o OUTPUT]
      cot <opts> edit-properties PACKAGE -c CONFIG_FILE [-o OUTPUT]
      cot <opts> edit-properties PACKAGE [-o OUTPUT]

    Configure environment properties of the given OVF or OVA. The user may
    specify key-value pairs as command-line arguments or may provide a config-
    file to read from. If neither are specified, the program will run
    interactively.

    positional arguments:
      PACKAGE               OVF descriptor or OVA file to edit

    general options:
      -h, --help            Show this help message and exit
      -o OUTPUT, --output OUTPUT
                            Name/path of new OVF/OVA package to create instead
                            of updating the existing OVF

    property setting options:
      -c CONFIG_FILE, --config-file CONFIG_FILE
                            Read configuration CLI from this text file and
                            generate generic properties for each line of CLI
      -p KEY1=VALUE1 [KEY2=VALUE2 ...], --properties KEY1=VALUE1 [KEY2=VALUE2 ...]
                            Set the given property key-value pair(s). This
                            argument may be repeated as needed to specify
                            multiple properties to edit.

`cot info`
----------

    > cot info -h
    usage:
      cot info --help
      cot info [-b | -v] PACKAGE [PACKAGE ...]

    Show a summary of the contents of the given OVF(s) and/or OVA(s).

    positional arguments:
      PACKAGE [PACKAGE ...]
                            OVF descriptor(s) and/or OVA file(s) to describe

    optional arguments:
      -h, --help            show this help message and exit
      -b, --brief           Brief output (shorter)
      -v, --verbose         Verbose output (longer)

`cot inject-config`
-------------------

    > cot inject-config -h
    usage:
      cot inject-config --help
      cot <opts> inject-config PACKAGE -c CONFIG_FILE [-o OUTPUT]
      cot <opts> inject-config PACKAGE -s SECONDARY_CONFIG_FILE [-o OUTPUT]
      cot <opts> inject-config PACKAGE -c CONFIG_FILE -s SECONDARY_CONFIG_FILE
                               [-o OUTPUT]

    Add one or more "bootstrap" configuration file(s) to the given OVF or OVA.

    positional arguments:
      PACKAGE               Package, OVF descriptor or OVA file to edit

    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUT, --output OUTPUT
                            Name/path of new VM package to create instead of
                            updating the existing package
      -c CONFIG_FILE, --config-file CONFIG_FILE
                            Primary configuration text file to embed
      -s SECONDARY_CONFIG_FILE, --secondary-config-file SECONDARY_CONFIG_FILE
                            Secondary configuration text file to embed
                            (currently only supported in IOS XRv for admin
                            config)
