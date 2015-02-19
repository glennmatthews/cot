Inspecting OVF contents with ``cot info``
=========================================

::

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
