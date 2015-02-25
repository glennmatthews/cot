Getting CLI help
================

You can always get detailed help for COT by running ``cot --help``,
``cot <command> --help``, or ``cot help <command>``.

::

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
        help            Print help for a command
        info            Generate a description of an OVF package
        inject-config   Inject a configuration file into an OVF package
        install-helpers
                        Install third-party helper programs that COT may require

    Note: some subcommands rely on external software tools, including:
    * qemu-img (http://www.qemu.org/)
    * mkisofs  (http://cdrecord.org/)
    * ovftool  (https://www.vmware.com/support/developer/ovf/)
    * fatdisk  (http://github.com/goblinhack/fatdisk)
    * vmdktool (http://www.freshports.org/sysutils/vmdktool/)
