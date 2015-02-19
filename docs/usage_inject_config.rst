Embedding bootstrap configuration with ``cot inject-config``
============================================================

::

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
