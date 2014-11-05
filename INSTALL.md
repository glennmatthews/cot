* [Mac OS X Installation](#mac-os-x-installation)
* [Linux Installation](#linux-installation)

Mac OS X Installation
=====================

The recommended installation method on Mac OS X is to use
[MacPorts](http://www.macports.org/). Once you have MacPorts set up on your
system, all you have to do is:

    sudo port install cot

Optionally, download [`ovftool`](https://www.vmware.com/support/developer/ovf/)
from VMware and install it. (VMware requires a site login to download `ovftool`,
which is the only reason I haven't automated this too...)

Linux Installation
==================

The specifics may vary depending on your Linux distribution, of course.

* [Check installed Python version](#check-installed-python-version)
* [Install Python `setuptools`](#install-python-setuptools)
* [Install Git (optional)](#install-git-optional)
* [Install QEMU](#install-qemu)
* [Install `vmdktool` (if needed)](#install-vmdktool-if-needed)
* [Install `fatdisk` (optional)](#install-fatdisk-optional)
* [Install `mkisofs` (optional)](#install-mkisofs-optional)
* [Install `ovftool` (optional)](#install-ovftool-optional)
* [Install COT](#install-cot)

Check installed Python version
------------------------------

Make sure your Python version is at least 2.7:

    > python --version
    Python 2.7.4

If it's an older release (CentOS in particular defaults to old Python versions)
then you need to install a newer version. Refer to http://www.python.org for
installation instructions.

Install Python `setuptools`
---------------------------
* Ubuntu and similar: `sudo apt-get install python-setuptools`

For other OS, refer to https://pythonhosted.org/setuptools/setuptools.html for
installation instructions.

Install Git (optional)
----------------------
Git makes it easier to obtain COT and `vmdktool` but it is not strictly
necessary - you can download source via HTTP if you do not have/want Git or
if Git is blocked by your environment.

* Ubuntu and similar: `sudo apt-get install git`

Install QEMU
------------

* Ubuntu and similar: `sudo apt-get install qemu`
* CentOS and similar: `sudo yum install qemu`

See http://en.wikibooks.org/wiki/QEMU/Installing_QEMU for other Linux variants.

Install `vmdktool` (if needed)
------------------------------

First, check your QEMU version to see if you even need `vmdktool`:

    $ qemu-img --version
    qemu-img version 2.1.0, Copyright (c) 2004-2008 Fabrice Bellard

If the reported version is 2.1.0 or newer, you don't need `vmdktool`.
If you have an older QEMU version and do need `vmdktool`:

1. Download the latest source distribution from
   http://people.freebsd.org/~brian/vmdktool:

        wget http://people.freebsd.org/~brian/vmdktool/vmdktool-1.4.tar.gz

2. Compile `vmdktool`:

        tar zxf vmdktool-1.4.tar.gz
        cd vmdktool-1.4/
        make

3. Install `vmdktool`:

        sudo make install

Install `fatdisk` (optional)
----------------------------

You only need `fatdisk` if you are planning to use `cot inject-config` to
inject bootstrap configuration for a platform that requires a hard disk image
rather than a CD-ROM image for its bootstrap disk.
Currently the only such platform known to COT is Cisco IOSv.

1. Download the latest source distribution.

        git clone git://github.com/goblinhack/fatdisk
        cd fatdisk

  or (if `git` is blocked for you)

        wget -O fatdisk.zip https://github.com/goblinhack/fatdisk/archive/master.zip
        unzip fatdisk.zip
        cd fatdisk-master

2. Compile `fatdisk`

        ./RUNME

3. Install the `fatdisk` binary to somewhere in your `$PATH`, for example:

        sudo cp ./fatdisk /usr/local/bin/fatdisk

Install `mkisofs` (optional)
----------------------------

[`mkisofs`](http://cdrecord.org/) is standard on most Linux distributions, but
if not installed on your system you may want to install it according to the
instructions at the linked web site.

Install `ovftool` (optional)
----------------------------

Download [`ovftool`](https://www.vmware.com/support/developer/ovf/)
from VMware and install it according to the included instructions.

Install COT
-----------

1. Download the latest source distribution. You can do this from the GitHub
  website (go to https://github.com/glennmatthews/cot/ and click
  ["Download Zip"](https://github.com/glennmatthews/cot/archive/master.zip)
  on the right side of the page), or you can do this via the CLI:

        git clone git://github.com/glennmatthews/cot
        cd cot

  or (if `git` is blocked for you):

        wget -O cot.zip https://github.com/glennmatthews/cot/archive/master.zip
        unzip cot.zip
        cd cot-master

2. While you can run COT directly from this directory (`./bin/cot ...`),
   you can also use the included `setup.py` script to install the COT
   modules and scripts as part of your system Python environment. In that case,
   build and test COT as follows:

        > python ./setup.py check
        running check
        > python ./setup.py build
        running build
        running build_py
        > python ./setup.py test
        running test

   (verbose test case output omitted here for brevity)

        ----------------------------------------------------------------------
        Ran 123 tests in 36.904s

        OK

   (If any tests fail, likely due to missing optional dependencies described
   above, the failures will be reported here, giving you a chance to fix them
   or ignore them before installing COT.)

3. Install COT:

        > sudo python ./setup.py install
        Password:
        running install

   (verbose install output omitted)

        Installing cot script to /usr/local/bin

        Installed /usr/local/lib/python2.7/dist-packages/common_ovf_tool-1.1.2-py2.7.egg
        Processing dependencies for common-ovf-tool==1.1.2
        Finished processing dependencies for common-ovf-tool==1.1.2
        > which cot
        /usr/local/bin/cot

   (the specific installation path will depend on your OS and system)

        > cot -h
        usage:
          cot --help
          cot --version
          cot <command> --help
          cot [-f] [-v] <command> <options>

        Common OVF Tool (COT), version 1.1.2
        Copyright (C) 2013-2014 the COT project developers
        A tool for editing Open Virtualization Format (.ovf, .ova) virtual appliances,
        with a focus on virtualized network appliances such as the Cisco CSR 1000V and
        Cisco IOS XRv platforms.
        ...
