Updating version information with ``cot edit-product``
======================================================

::

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
