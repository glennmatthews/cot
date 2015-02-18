Customizing OVF environment settings with ``cot edit-properties``
=================================================================

::

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
