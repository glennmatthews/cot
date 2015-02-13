Installing COT
==============

System requirements
-------------------

* COT requires either Python 2.7 or Python 3.2 or later.
* COT is tested to work under Mac OS X and Ubuntu Linux and similar distros.
* COT now has limited support for CentOS and Python 2.6 as well.
* Certain COT features require helper programs - these will typically be
  installed automatically when installing COT:

  * COT uses `qemu-img`_ as a helper program for various operations involving
    the creation, inspection, and modification of hard disk image files
    packaged in an OVF.
  * The ``cot add-disk`` command requires either `qemu-img`_ (version 2.1 or
    later) or vmdktool_ as a helper program when adding hard disks to an OVF.
  * The ``cot inject-config`` command requires mkisofs_ to create ISO
    (CD-ROM) images and/or `fatdisk`_ to create hard disk images.
  * The ``cot deploy ... esxi`` command requires ovftool_ to communicate
    with an ESXi server. If ovftool is installed, COT's automated unit tests
    will also make use of ovftool to perform additional verification that
    OVFs and OVAs created by COT align with VMware's expectations for these
    file types.

Mac OS X installation
---------------------

The recommended installation method on Mac OS X is to use MacPorts_.
Once you have MacPorts set up on your system, all you have to do is:

::

  sudo port install cot

Optionally, download ovftool_ from VMware and install it.
(VMware requires a site login to download ovftool,
which is the only reason I haven't automated this too...)

Linux installation
------------------

The simplest installation path (assuming you have Python 2.6 or later and
Git installed already) is as follows:

::

  git clone git://github.com/glennmatthews/cot
  cd cot
  python ./setup.py build
  sudo python ./setup.py install

If you can't install or use Git for whatever reason, you can download via HTTP
instead:

::

  wget -O cot.tgz https://github.com/glennmatthews/cot/archive/master.tar.gz
  tar zxf cot.tgz
  cd cot-master
  python setup.py build
  sudo python setup.py install

The specifics may vary depending on your Linux distribution, of course.
For more details you can refer to the `INSTALL_LINUX.md`_ file.

Optionally, download ovftool_ from VMware and install it.
(VMware requires a site login to download ovftool,
which is the only reason I haven't automated this too...)


.. _qemu-img: http://www.qemu.org
.. _vmdktool: http://www.freshports.org/sysutils/vmdktool/
.. _mkisofs: http://cdrecord.org/
.. _fatdisk: http://github.com/goblinhack/fatdisk
.. _ovftool: https://www.vmware.com/support/developer/ovf/
.. _MacPorts: http://www.macports.org/
.. _`INSTALL_LINUX.md`: https://github.com/glennmatthews/cot/blob/master/INSTALL_LINUX.md
