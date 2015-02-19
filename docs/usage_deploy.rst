Deploying an OVF to create a VM with ``cot deploy``
===================================================

::

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

Creating a VM on VMware vCenter/vSphere with ``cot deploy esxi``
----------------------------------------------------------------

::

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
