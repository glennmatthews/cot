COT: the Common OVF Tool
************************

.. image:: https://img.shields.io/pypi/v/cot.svg
    :target: https://pypi.python.org/pypi/cot/
    :alt: Latest Version
.. image:: https://img.shields.io/badge/license-MIT-blue.svg
    :target: https://pypi.python.org/pypi/cot/
    :alt: License
.. image:: https://travis-ci.org/glennmatthews/cot.svg?branch=master
    :target: https://travis-ci.org/glennmatthews/cot
    :alt: Build Status
.. image:: https://coveralls.io/repos/glennmatthews/cot/badge.svg?branch=master
    :target: https://coveralls.io/r/glennmatthews/cot?branch=master
    :alt: Coverage Status
.. image:: https://readthedocs.org/projects/cot/badge/?version=latest
    :target: https://readthedocs.org/projects/cot/?badge=latest
    :alt: Documentation Status

COT (the Common OVF Tool) is a tool for editing `Open Virtualization Format`_
(``.ovf``, ``.ova``) virtual appliances, with a focus on virtualized network
appliances such as the `Cisco CSR 1000V`_ and `Cisco IOS XRv`_ platforms.

COT's capabilities include:

* Add a disk or other file to an OVF/OVA
* Edit OVF hardware information (CPUs, RAM, NICs, configuration profiles, etc.)
* Edit product description information in an OVF/OVA
* Edit OVF environment properties
* Display a descriptive summary of the contents of an OVA or OVF package
* Embed a bootstrap configuration text file into an OVF/OVA.
* Deploy an OVF/OVA to an ESXi (VMware vSphere or vCenter) server to provision
  a new virtual machine (VM), including serial port configuration as needed.

For more information, refer to the documentation_.

.. _`Open Virtualization Format`: http://dmtf.org/standards/ovf
.. _`Cisco CSR 1000V`: http://www.cisco.com/go/csr1000v
.. _`Cisco IOS XRv`: http://www.cisco.com/go/iosxrv
.. _documentation: http://cot.readthedocs.org/
