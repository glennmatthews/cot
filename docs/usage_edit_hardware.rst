Customizing hardware profiles with ``cot edit-hardware``
========================================================

::

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

