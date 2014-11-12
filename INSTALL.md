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

The simplest installation path (assuming you have Python 2.6 or later and
Git installed already) is as follows:

    git clone git://github.com/glennmatthews/cot
    cd cot
    python ./setup.py build
    sudo python ./setup.py install

If you can't install or use Git for whatever reason, you can download via HTTP
instead:

    wget -O cot.tgz https://github.com/glennmatthews/cot/archive/master.tar.gz
    tar zxf cot.tgz
    cd cot-master
    python setup.py build
    sudo python setup.py install

The specifics may vary depending on your Linux distribution, of course.
For more details you can refer to the
[INSTALL_LINUX.md](https://github.com/glennmatthews/cot/blob/master/INSTALL_LINUX.md)
file.

Optionally, download [`ovftool`](https://www.vmware.com/support/developer/ovf/)
from VMware and install it. (VMware requires a site login to download `ovftool`,
which is the only reason I haven't automated this too...)
