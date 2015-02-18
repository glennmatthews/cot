Linux installation in detail
============================

Detailed installation instructions for Linux if the basic instructions from
:doc:`installation` are insufficient.

.. contents::
   :local:


Check installed Python version
------------------------------

Make sure your Python version is ideally at least 2.7 or 3.2:

::

  > python --version
  Python 2.7.4

CentOS in particular defaults to Python 2.6 - COT can be installed and
run under Python 2.6 but this is not optimal. See below for more details.

Download COT
------------

You can download COT via either HTTP or via Git.

Downloading COT via HTTP
''''''''''''''''''''''''

To download the latest bleeding-edge version:

::

    wget -O cot.tgz https://github.com/glennmatthews/cot/archive/master.tar.gz
    tar zxf cot.tgz
    cd cot-master

To download a specific stable release (in this example, v1.2.1):

::

    wget -O cot.tgz https://github.com/glennmatthews/cot/archive/v1.2.1.tar.gz
    tar zxf cot.tgz
    cd cot-1.2.1

Downloading COT via Git
'''''''''''''''''''''''

Under Ubuntu and similar, you may need to run ``sudo apt-get install git``.
Under CentOS and similar, you may need to run ``sudo yum install git``.

Make a local clone of the Git repository:

::

    git clone git://github.com/glennmatthews/cot
    cd cot

This will default to the latest bleeding-edge version. If you want a specific
stable release, use the following command to select to the desired release
(for example, version 1.2.1):

::

    git checkout tags/v1.2.1

Build COT
---------

While you can run COT directly from this directory (``./bin/cot ...``),
you can also use the included ``setup.py`` script to install the COT
modules and scripts as part of your system Python environment. In that case,
build and test COT as follows:

::

    > python ./setup.py check
    running check
    > python ./setup.py build
    running build
    running build_py

Install helper programs
-----------------------

Once you have verified your Python version, run the following command to check
for and install the various helper programs COT relies upon.

::

    sudo python ./setup.py install_helpers

If any helpers are missing, the script will warn you and give you an option to
attempt to automatically install them. If it tries and fails to do so, it will
point you to the web site for the failed tool - but *please* post an issue on
GitHub (https://github.com/glennmatthews/cot/issues) so that we can identify the
failure and work to improve this script.

If for some reason you do not wish to use the above script, or would like to
understand exactly what it's doing, see the following sections:

.. contents::
  :local:

In any case, once the helper tools you need are installed, you can proceed to
`Install COT`_.

Install ``qemu-img``
''''''''''''''''''''

* Ubuntu and similar: ``sudo apt-get install qemu``
* CentOS and similar: ``sudo yum install qemu-img``

See http://en.wikibooks.org/wiki/QEMU/Installing_QEMU for other Linux variants.

Install ``vmdktool`` (if needed)
''''''''''''''''''''''''''''''''

First, check your QEMU version to see if you even need ``vmdktool``:

::

    $ qemu-img --version | grep " version"
    qemu-img version 2.1.0, Copyright (c) 2004-2008 Fabrice Bellard

If the reported version is 2.1.0 or newer, you don't need ``vmdktool``.
If you have an older QEMU version and do need ``vmdktool``:

1. Install ``make`` and the library ``zlib`` that ``vmdktool`` depends on:

  * Ubuntu and similar: ``sudo apt-get install make``,
    ``sudo apt-get install zlib1g-dev``
  * CentOS and similar: ``sudo yum install make``,
    ``sudo yum install zlib-devel``

2. Download the latest source distribution from
   http://people.freebsd.org/~brian/vmdktool:

   ::

        wget http://people.freebsd.org/~brian/vmdktool/vmdktool-1.4.tar.gz

3. Compile ``vmdktool``:

   ::

        tar zxf vmdktool-1.4.tar.gz
        cd vmdktool-1.4/
        make CFLAGS="-D_GNU_SOURCE"

4. Install ``vmdktool``:

   ::

        sudo mkdir -p /usr/local/man/man8
        sudo make install

Install ``fatdisk`` (optional)
''''''''''''''''''''''''''''''

You only need ``fatdisk`` if you are planning to use ``cot inject-config`` to
inject bootstrap configuration for a platform that requires a hard disk image
rather than a CD-ROM image for its bootstrap disk.
Currently the only such platform known to COT is Cisco IOSv.

1. Download the latest source distribution.

   ::

      git clone git://github.com/goblinhack/fatdisk
      cd fatdisk

   or (if you didn't install ``git`` or it is blocked for you)

   ::

      wget -O fatdisk.tgz https://github.com/goblinhack/fatdisk/archive/master.tar.gz
      tar zxf fatdisk.tgz
      cd fatdisk-master

2. Compile ``fatdisk``

   ::

      ./RUNME

3. Install the ``fatdisk`` binary to somewhere in your ``$PATH``, for example:

   ::

        sudo cp ./fatdisk /usr/local/bin/fatdisk

Install ``mkisofs`` or ``genisoimage`` (optional)
'''''''''''''''''''''''''''''''''''''''''''''''''

mkisofs_ or the similar ``genisoimage`` are standard on
most Linux distributions. These are used by COT primarily for creation of ISO
images as part of the ``cot inject-config`` command for various platforms, so if
you are not using that command, these tools are optional.

* Ubuntu and similar: ``sudo apt-get install genisoimage``
* CentOS and similar: ``sudo yum install genisoimage``
* Others: http://cdrecord.org/

Install ``ovftool`` (optional)
''''''''''''''''''''''''''''''

If you want to validate OVFs against VMware's expectations, or if you want to
use the ``cot deploy esxi`` command, you need ``ovftool``. Otherwise it is not
required.

If desired, you can download ``ovftool`` from
https://www.vmware.com/support/developer/ovf/
This will require creating a user account for VMware.com if you do not have
one already. Once downloaded, install it according to the included instructions.

Install COT
-----------

1. Before installing COT, if you want to, you can run its built-in unit tests
   as follows:

   ::

        > python ./setup.py test
        running test

   (verbose test case output omitted here for brevity)

   ::

        ----------------------------------------------------------------------
        Ran 136 tests in 41.130s

        OK

   Note that under Python 2.6 (i.e., CentOS) this test will report numerous
   test skips at present as the XML generated by Python 2.6 is structured
   differently (but still valid!) from the XML generated by 2.7 and later,
   and the unit tests do not presently support this variance.

   If any tests fail, likely due to missing optional dependencies described
   above, the failures will be reported here, giving you a chance to fix them
   or ignore them before installing COT.

2. Install COT:

   ::

        > sudo python ./setup.py install
        Password:
        running install

   (verbose install output omitted)

   ::

        Installing cot script to /usr/local/bin

        Installed /usr/local/lib/python2.7/dist-packages/common_ovf_tool-1.2.1-py2.7.egg
        Processing dependencies for common-ovf-tool==1.2.1
        Finished processing dependencies for common-ovf-tool==1.2.1
        > which cot
        /usr/local/bin/cot

   (the specific installation path will depend on your OS and system)

   ::

        > cot -h
        usage:
          cot --help
          cot --version
          cot <command> --help
          cot [-f] [-v] <command> <options>

        Common OVF Tool (COT), version 1.2.1
        Copyright (C) 2013-2015 the COT project developers
        A tool for editing Open Virtualization Format (.ovf, .ova) virtual appliances,
        with a focus on virtualized network appliances such as the Cisco CSR 1000V and
        Cisco IOS XRv platforms.
        ...


.. _mkisofs: http://cdrecord.org/
