Packaging additional files into an OVF with ``cot add-file``
============================================================

::

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
