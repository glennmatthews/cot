Adding disks to an OVF with ``cot add-disk``
============================================

::

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
