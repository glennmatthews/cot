Common OVF Tool (COT)
=====================

[![Latest Version](https://img.shields.io/pypi/v/cot.svg)](https://pypi.python.org/pypi/cot/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://pypi.python.org/pypi/cot/)
[![build status](https://api.travis-ci.org/glennmatthews/cot.svg?branch=master)](https://travis-ci.org/glennmatthews/cot)
[![Coverage Status](https://coveralls.io/repos/glennmatthews/cot/badge.svg?branch=master)](https://coveralls.io/r/glennmatthews/cot?branch=master)
[![Documentation Status](https://readthedocs.org/projects/cot/badge/?version=latest)](https://readthedocs.org/projects/cot/?badge=latest)

COT (the Common OVF Tool) is a tool for editing
[Open Virtualization Format](http://dmtf.org/standards/ovf)
(`.ovf`, `.ova`) virtual appliances, with a focus on virtualized network
appliances such as the [Cisco CSR 1000V](http://www.cisco.com/go/csr1000v)
and [Cisco IOS XRv](http://www.cisco.com/go/iosxrv) platforms.

COT's capabilities include:

* Add a disk or other file to an OVF/OVA
* Edit OVF hardware information (CPUs, RAM, NICs, configuration profiles, etc.)
* Edit product description information in an OVF/OVA
* Edit OVF environment properties
* Display a descriptive summary of the contents of an OVA or OVF package
* Embed a bootstrap configuration text file into an OVF/OVA.
* Deploy an OVF/OVA to an ESXi (VMware vSphere or vCenter) server to provision
  a new virtual machine (VM), including serial port configuration as needed.

For more information, refer to the
[documentation](http://cot.readthedocs.org/).
