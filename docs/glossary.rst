Glossary
========

.. default-role:: term

.. glossary::

  COT
    Common `OVF` Tool

  controller
  hardware controller
    A virtual hardware controller for hardware such as a `disk device`.
    In addition to its primary type (IDE, SCSI, etc.), a controller may also
    have a subtype, such as ``virtio`` or ``lsilogic``.
    In an `OVF` package, a controller is represented by an XML ``Item``
    element in the ``VirtualHardwareSection`` of the `OVF descriptor`.
    Typically each `disk device` must be associated with a controller.

  disk description
  disk element
  disk reference
    A description of a virtual disk included in a virtual machine.
    In an `OVF descriptor`, this is an XML ``Disk`` element in the
    ``DiskSection``.
    This disk description may be associated with a `file reference` and/or
    `disk file`, or it may be a placeholder for a blank disk not yet created.
    Typically a disk description must be associated with a `disk drive` in
    order to actually be accessible by the guest OS.

  disk device
  disk drive
  disk item
    A `hardware item` describing a virtual CD-ROM, DVD-ROM, or hard disk drive.
    In an `OVF` package, this is an XML ``Item`` element in the
    ``VirtualHardwareSection`` of the `OVF descriptor`.
    This item may reference a `disk reference` or a `file reference` to map
    a filesystem to this drive.
    Typically a disk drive must be associated to a `hardware controller`.

  disk file
  disk image
    A file such as a .vmdk, .iso, or .qcow2. May or may not be associated with
    a `disk drive`.

  file element
  file reference
    A reference to a file, such as a `disk file` or any other file type,
    to be included in a virtual machine.
    In an `OVF descriptor`, this is an XML ``File`` element in the
    ``References`` section.

  hardware element
  hardware item
    Generic term for any discrete piece of virtual machine hardware, including
    but not limited to the CPU(s), memory, `disk drive`, `hardware controller`,
    network port, etc.

  OVF
    `Open Virtualization Format`_, an open standard.

  OVF descriptor
    An XML file, based on the `OVF` specification, which describes a
    virtual machine.

.. _`Open Virtualization Format`: http://dmtf.org/standards/ovf
