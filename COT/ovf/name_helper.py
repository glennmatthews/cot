#!/usr/bin/env python
#
# name_helper.py - Handling the many XML names in an OVF descriptor
#
# June 2016, Glenn F. Matthews
# Copyright (c) 2013-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.
"""Module for handling the differences in XML between OVF spec versions.

**Functions**

.. autosummary::
  :nosignatures:

  name_helper

**Classes and Exceptions**

.. autosummary::
  :nosignatures:

  OVFNameHelper1
  OVFNameHelper0
  OVFNameHelper2
"""

from COT.data_validation import ValueUnsupportedError


def name_helper(version):
    """Generate an instance of the correct OVFNameHelper variant class.

    :param float version: OVF specification version to use, such as 0.9,
      1.0, or 2.0
    :return: Instance of OVFNameHelper[012] as appropriate.
    """
    if version < 1.0:
        return OVFNameHelper0()
    elif version < 2.0:
        return OVFNameHelper1()
    else:
        return OVFNameHelper2()


class _Tag(object):
    """Helper class representing a named XML namespace and associated tag."""

    def __init__(self, namespace_name, tag):
        self.namespace_name = namespace_name.upper()
        self.tag = tag


CIM_URI = "http://schemas.dmtf.org/wbem/wscim/1"


class OVFNameHelper1(object):
    """Helper class for :class:`OVF` version 1.x.

    Provides string constants for easier lookup of various OVF XML
    elements and attributes.

    Version-specific subclasses below provide variant properties.
    """

    # For the standard namespace URIs in an OVF descriptor, let's define
    # shorthand identifiers to be used when writing back out to XML:
    NSM = dict(
        xsi="http://www.w3.org/2001/XMLSchema-instance",
        cim=CIM_URI + "/common",
        rasd=CIM_URI + "/cim-schema/2/CIM_ResourceAllocationSettingData",
        vssd=CIM_URI + "/cim-schema/2/CIM_VirtualSystemSettingData",
        # The OVF namespace varies by version
        ovf="http://schemas.dmtf.org/ovf/envelope/1",
        # Older OVF versions have ethernet and storage items
        # in the same RASD namespace as other hardware, but 2.x has separate
    )

    # Non-standard namespaces (such as VMWare's
    # 'http://www.vmware.com/schema/ovf') should not be added to the NSM
    # dictionary, but may be registered manually by calling
    # register_namespace() as needed - see OVF.write() for examples.

    # List of ResourceType string values we know about
    # http://schemas.dmtf.org/wbem/cim-html/2/
    #        CIM_ResourceAllocationSettingData.html
    RES_MAP = {
        'cpu':       '3',
        'memory':    '4',
        'ide':       '5',
        'scsi':      '6',
        'fc':        '7',
        'iscsi':     '8',
        'ib':        '9',
        'ethernet': '10',
        'floppy':   '14',
        'cdrom':    '15',
        'dvd':      '16',
        'harddisk': '17',
        'sata':     '20',   # 'Other Storage' but VBox uses for SATA
        'serial':   '21',
        'parallel': '22',
        'usb':      '23',
    }

    # Cached strings, built on the fly
    _cache = {}

    # XML elements we care about in the OVF descriptor
    # TagPlusNamespace objects
    _raw = dict(
        # Top-level element is Envelope
        ENVELOPE=_Tag('ovf', 'Envelope'),

        # All Section elements have an Info element as child
        INFO=_Tag('ovf', 'Info'),

        # Envelope -> NetworkSection -> Network
        NETWORK_SECTION=_Tag('ovf', 'NetworkSection'),
        NETWORK=_Tag('ovf', 'Network'),

        # Attributes of a Network element
        NETWORK_NAME=_Tag('ovf', 'name'),

        # Network sub-elements
        NWK_DESC=_Tag('ovf', 'Description'),

        # Envelope -> DeploymentOptionSection -> Configuration
        DEPLOY_OPT_SECTION=_Tag('ovf', 'DeploymentOptionSection'),
        CONFIG=_Tag('ovf', 'Configuration'),

        # Attributes of a Configuration element
        CONFIG_ID=_Tag('ovf', 'id'),
        CONFIG_DEFAULT=_Tag('ovf', 'default'),

        # Configuration sub-elements
        CFG_LABEL=_Tag('ovf', 'Label'),
        CFG_DESC=_Tag('ovf', 'Description'),

        # Envelope -> References -> File
        REFERENCES=_Tag('ovf', 'References'),
        FILE=_Tag('ovf', 'File'),

        # Attributes of a File element
        FILE_ID=_Tag('ovf', 'id'),
        FILE_HREF=_Tag('ovf', 'href'),
        FILE_SIZE=_Tag('ovf', 'size'),

        # Envelope -> DiskSection -> Disk
        DISK_SECTION=_Tag('ovf', 'DiskSection'),
        DISK=_Tag('ovf', 'Disk'),

        # Attributes of a Disk element
        DISK_ID=_Tag('ovf', 'diskId'),
        DISK_FILE_REF=_Tag('ovf', 'fileRef'),
        DISK_CAPACITY=_Tag('ovf', 'capacity'),
        DISK_CAP_UNITS=_Tag('ovf', 'capacityAllocationUnits'),
        DISK_FORMAT=_Tag('ovf', 'format'),

        # Envelope -> VirtualSystem -> AnnotationSection -> Annotation
        ANNOTATION_SECTION=_Tag('ovf', 'AnnotationSection'),
        ANNOTATION=_Tag('ovf', 'Annotation'),

        # Envelope -> VirtualSystem -> ProductSection
        VIRTUAL_SYSTEM=_Tag('ovf', 'VirtualSystem'),
        PRODUCT_SECTION=_Tag('ovf', 'ProductSection'),

        # ProductSection attributes
        PRODUCT_CLASS=_Tag('ovf', 'class'),

        # ProductSection sub-elements
        PRODUCT=_Tag('ovf', 'Product'),
        VENDOR=_Tag('ovf', 'Vendor'),
        VERSION=_Tag('ovf', 'Version'),
        FULL_VERSION=_Tag('ovf', 'FullVersion'),
        PRODUCT_URL=_Tag('ovf', 'ProductUrl'),
        VENDOR_URL=_Tag('ovf', 'VendorUrl'),
        APPLICATION_URL=_Tag('ovf', 'AppUrl'),
        PROPERTY=_Tag('ovf', 'Property'),

        # Attributes of a Property element
        PROP_KEY=_Tag('ovf', 'key'),
        PROP_VALUE=_Tag('ovf', 'value'),
        PROP_QUAL=_Tag('ovf', 'qualifiers'),
        PROP_TYPE=_Tag('ovf', 'type'),

        # Property sub-elements
        PROPERTY_LABEL=_Tag('ovf', 'Label'),
        PROPERTY_DESC=_Tag('ovf', 'Description'),

        ENVIRONMENT_TRANSPORT=_Tag('ovf', 'transport'),

        # Envelope -> VirtualSystem -> EulaSection -> License
        EULA_SECTION=_Tag('ovf', 'EulaSection'),
        EULA_LICENSE=_Tag('ovf', 'License'),

        # Envelope -> VirtualSystem -> VirtualHardwareSection -> Item(s)
        # In version 2.x, there can also be StorageItem and EthernetPortItem
        VIRTUAL_HW_SECTION=_Tag('ovf', 'VirtualHardwareSection'),
        ITEM=_Tag('ovf', 'Item'),
        # These are just regular Items in older OVF versions
        STORAGE_ITEM=_Tag('ovf', 'Item'),
        ETHERNET_PORT_ITEM=_Tag('ovf', 'Item'),

        # Item attributes
        ITEM_CONFIG=_Tag('ovf', 'configuration'),

        # ... VirtualHardwareSection -> System -> VirtualSystemType
        SYSTEM=_Tag('ovf', 'System'),
        VIRTUAL_SYSTEM_TYPE=_Tag('vssd', 'VirtualSystemType'),
    )

    # Item sub-elements
    # As these are shared across the RASD, SASD, and EPASD namespaces
    # in OVF 2.0, we don't hard-code a namespace any more.
    _item_children = dict(
        ADDRESS='Address',
        ADDRESS_ON_PARENT='AddressOnParent',
        ALLOCATION_UNITS='AllocationUnits',
        AUTOMATIC_ALLOCATION='AutomaticAllocation',
        AUTOMATIC_DEALLOCATION='AutomaticDeallocation',
        CAPTION='Caption',
        CONNECTION='Connection',
        CONSUMER_VISIBILITY='ConsumerVisibility',
        ITEM_DESCRIPTION='Description',
        ELEMENT_NAME='ElementName',
        HOST_RESOURCE='HostResource',
        OLD_HOST_RSRC_FILE_REF="/file/",
        OLD_HOST_RSRC_DISK_REF="/disk/",
        HOST_RSRC_FILE_REF="ovf:/file/",
        HOST_RSRC_DISK_REF="ovf:/disk/",
        INSTANCE_ID='InstanceID',
        LIMIT='Limit',
        MAPPING_BEHAVIOR='MappingBehavior',
        OTHER_RESOURCE_TYPE='OtherResourceType',
        PARENT='Parent',
        POOL_ID='PoolID',
        RESERVATION='Reservation',
        RESOURCE_SUB_TYPE='ResourceSubType',
        RESOURCE_TYPE='ResourceType',
        VIRTUAL_QUANTITY='VirtualQuantity',
        WEIGHT='Weight',
    )

    def __getattr__(self, name):
        """Transparently pass attribute lookups to _raw and _cache."""
        if name in self._item_children:
            return self._item_children[name]
        if name not in self._cache:
            if name.lower() in self.NSM:
                self._cache[name] = "{%s}" % self.NSM[name.lower()]
            elif name == "EPASD" or name == "SASD":
                self._cache[name] = self.RASD
            elif name not in self._raw:
                raise AttributeError
            else:
                ns = getattr(self, self._raw[name].namespace_name)
                tag = self._raw[name].tag
                self._cache[name] = ns + tag
        return self._cache[name]

    def __init__(self):
        """Create a name helper for OVF version 1.x."""
        # 1.0 is nice in that they're all in alphabetical order
        self.ITEM_CHILDREN = (
            self.ADDRESS,
            self.ADDRESS_ON_PARENT,
            self.ALLOCATION_UNITS,
            self.AUTOMATIC_ALLOCATION,
            self.AUTOMATIC_DEALLOCATION,
            self.CAPTION,
            self.CONNECTION,
            self.CONSUMER_VISIBILITY,
            self.ITEM_DESCRIPTION,
            self.ELEMENT_NAME,
            self.HOST_RESOURCE,
            self.INSTANCE_ID,
            self.LIMIT,
            self.MAPPING_BEHAVIOR,
            self.OTHER_RESOURCE_TYPE,
            self.PARENT,
            self.POOL_ID,
            self.RESERVATION,
            self.RESOURCE_SUB_TYPE,
            self.RESOURCE_TYPE,
            self.VIRTUAL_QUANTITY,
            self.WEIGHT,
        )

        # all of these are 0.9 exclusive

        self.NETWORK_SECTION_ATTRIB = {}
        self.DISK_SECTION_ATTRIB = {}
        self.ANNOTATION_SECTION_ATTRIB = {}
        self.VIRTUAL_SYSTEM_ATTRIB = {}
        self.PRODUCT_SECTION_ATTRIB = {}
        self.EULA_SECTION_ATTRIB = {}
        self.VIRTUAL_HW_SECTION_ATTRIB = {}

    def namespace_for_item_tag(self, tag):
        """Get the XML namespace for the given item tag."""
        if tag == self.ITEM:
            return self.RASD
        elif tag == self.STORAGE_ITEM:
            return self.SASD
        elif tag == self.ETHERNET_PORT_ITEM:
            return self.EPASD
        return None

    def namespace_for_resource_type(self, resource_type):
        """Get the XML namespace for the given ResourceType."""
        if resource_type == self.RES_MAP['ethernet']:
            return self.EPASD
        elif (resource_type == self.RES_MAP['harddisk'] or
              resource_type == self.RES_MAP['cdrom']):
            return self.SASD
        else:
            return self.RASD

    def item_tag_for_namespace(self, ns):
        """Get the item tag for the given XML namespace."""
        if ns == self.RASD:
            return self.ITEM
        elif ns == self.SASD:
            return self.STORAGE_ITEM
        elif ns == self.EPASD:
            return self.ETHERNET_PORT_ITEM
        else:
            raise ValueUnsupportedError("namespace",
                                        ns,
                                        [self.RASD, self.SASD, self.EPASD])


class OVFNameHelper0(OVFNameHelper1):
    """Helper class for :class:`OVF` of versions prior to 1.0.

    Provides string constants for easier lookup of various OVF XML
    elements and attributes.
    """

    NSM = dict(
        OVFNameHelper1.NSM,
        ovf="http://www.vmware.com/schema/ovf/1/envelope",
    )
    _cache = dict(OVFNameHelper1._cache)
    _raw = dict(
        OVFNameHelper1._raw,
        NETWORK_SECTION=_Tag('ovf', 'Section'),
        DISK_SECTION=_Tag('ovf', 'Section'),
        ANNOTATION_SECTION=_Tag('ovf', 'Section'),
        VIRTUAL_SYSTEM=_Tag('ovf', 'Content'),
        PRODUCT_SECTION=_Tag('ovf', 'Section'),
        PROP_VALUE=_Tag('ovf', 'defaultValue'),
        EULA_SECTION=_Tag('ovf', 'Section'),
        VIRTUAL_HW_SECTION=_Tag('ovf', 'Section'),
    )
    _item_children = dict(
        OVFNameHelper1._item_children,
        BUS_NUMBER='BusNumber',
        # No ElementName in 0.9, but Caption serves a similar purpose
        ELEMENT_NAME='Caption',
        HOST_RSRC_FILE_REF="/file/",
        HOST_RSRC_DISK_REF="/disk/",
        INSTANCE_ID='InstanceId',
    )

    def __init__(self):
        """Create a name helper for OVF version 0.x."""
        super(OVFNameHelper0, self).__init__()
        self.ITEM_CHILDREN = (
            self.CAPTION,
            self.ITEM_DESCRIPTION,
            self.INSTANCE_ID,
            self.RESOURCE_TYPE,
            self.OTHER_RESOURCE_TYPE,
            self.RESOURCE_SUB_TYPE,
            self.POOL_ID,
            self.CONSUMER_VISIBILITY,
            self.HOST_RESOURCE,
            self.ALLOCATION_UNITS,
            self.VIRTUAL_QUANTITY,
            self.RESERVATION,
            self.LIMIT,
            self.WEIGHT,
            self.AUTOMATIC_ALLOCATION,
            self.AUTOMATIC_DEALLOCATION,
            self.PARENT,
            self.CONNECTION,
            self.ADDRESS,
            self.MAPPING_BEHAVIOR,
            self.ADDRESS_ON_PARENT,
            self.BUS_NUMBER,
        )

        xsi_type = "{" + self.NSM['xsi'] + "}type"
        self.NETWORK_SECTION_ATTRIB = {
            xsi_type: "ovf:NetworkSection_Type"
        }
        self.DISK_SECTION_ATTRIB = {
            xsi_type: "ovf:DiskSection_Type"
        }
        self.ANNOTATION_SECTION_ATTRIB = {
            xsi_type: "ovf:AnnotationSection_Type"
        }
        self.VIRTUAL_SYSTEM_ATTRIB = {
            xsi_type: "ovf:VirtualSystem_Type"
        }
        self.PRODUCT_SECTION_ATTRIB = {
            xsi_type: "ovf:ProductSection_Type"
        }
        self.EULA_SECTION_ATTRIB = {
            xsi_type: "ovf:EulaSection_Type"
        }
        self.VIRTUAL_HW_SECTION_ATTRIB = {
            xsi_type: "ovf:VirtualHardwareSection_Type"
        }


class OVFNameHelper2(OVFNameHelper1):
    """Helper class for :class:`OVF` of version 2.x. TODO.

    Provides string constants for easier lookup of various OVF XML
    elements and attributes.
    """

    NSM = dict(
        OVFNameHelper1.NSM,
        ovf="http://schemas.dmtf.org/ovf/envelope/2",
        # OVF 2.0 adds new namespaces for ethernet ports & storage devices
        epasd=(CIM_URI +
               "/cim-schema/2/CIM_EthernetPortAllocationSettingData.xsd"),
        sasd=(CIM_URI +
              "/cim-schema/2/CIM_StorageAllocationSettingData.xsd"),
    )
    _cache = dict(OVFNameHelper1._cache)
    _raw = dict(
        OVFNameHelper1._raw,
        STORAGE_ITEM=_Tag('ovf', 'StorageItem'),
        ETHERNET_PORT_ITEM=_Tag('ovf', 'EthernetPortItem'),
    )

    def __init__(self):
        """Create a name helper for OVF version 2.x."""
        super(OVFNameHelper2, self).__init__()
