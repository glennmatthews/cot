Verifying and installing helper programs with ``cot install-helpers``
=====================================================================

::

  > cot install-helpers -h
  usage:
    cot install-helpers --help
    cot <opts> install-helpers --verify-only
    cot <opts> install-helpers [--ignore-errors]

  Install third-party helper programs for COT

  optional arguments:
    -h, --help           show this help message and exit
    --verify-only        Only verify helpers -- do not attempt to install any
                         missing helpers.
    -i, --ignore-errors  Do not fail even if helper installation fails.


Verifying helpers
-----------------

You can verify whether COT can find all expected helper programs by running
``cot install-helpers --verify-only``:

::

  > cot install-helpers --verify-only
  Results:
  -------------
  fatdisk:      present at /opt/local/bin/fatdisk
  mkisofs:      present at /opt/local/bin/mkisofs
  ovftool:      present at /usr/local/bin/ovftool
  qemu-img:     present at /opt/local/bin/qemu-img
  vmdktool:     NOT FOUND

Installing helpers
------------------

If one or more of the helpers are not installed on your system, you can
let COT attempt to install them for you by running ``cot install-helpers``.
Note that most of the helpers will require administrator / ``sudo`` privileges,
which COT will prompt you for if necessary.

If any installation fails, COT will exit with an error, unless you use the
``--ignore-errors`` option to prevent this.

Example:

::

    cot install-helpers
        INFO: Installing 'fatdisk'...
        INFO: Compiling 'fatdisk'
        INFO: Calling './RUNME'...
    (...)
        INFO: ...done
        INFO: Compilation complete, installing now
        INFO: Calling 'sudo cp fatdisk /usr/local/bin/fatdisk'...
        INFO: ...done
        INFO: Successfully installed 'fatdisk'
        INFO: Installing 'vmdktool'...
        INFO: vmdktool requires 'zlib'... installing 'zlib'
        INFO: Calling 'sudo apt-get -q install zlib1g-dev'...
    (...)
        INFO: ...done
        INFO: Compiling 'vmdktool'
        INFO: Calling 'make CFLAGS="-D_GNU_SOURCE -g -O -pipe"'...
    (...)
        INFO: ...done
        INFO: Compilation complete, installing now.
        INFO: Calling 'sudo mkdir -p --mode=755 /usr/local/man/man8'...
        INFO: ...done
        INFO: Calling 'sudo make install'...
    install -s vmdktool /usr/local/bin/
    install vmdktool.8 /usr/local/man/man8/
        INFO: ...done
        INFO: Successfully installed 'vmdktool'
    Results:
    -------------
    fatdisk:      successfully installed to /usr/local/bin/fatdisk
    mkisofs:      present at /usr/bin/mkisofs
    ovftool:      INSTALLATION FAILED: No support for automated installation of
                  ovftool, as VMware requires a site login to download it. See
                  https://www.vmware.com/support/developer/ovf/
    qemu-img:     present at /usr/bin/qemu-img
    vmdktool:     successfully installed to /usr/local/bin/vmdktool

    Unable to install some helpers

.. warning::
  Unfortunately, VMware requires a site login to download ovftool_, so if you
  need this tool, you will have to install it yourself. COT cannot install it
  for you at present.

.. _ovftool: https://www.vmware.com/support/developer/ovf/
