#!/usr/bin/env python
#
# hardware.py - OVFHardware class
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

"""Representation of OVF hardware definitions.

**Classes and Exceptions**

.. autosummary::
  :nosignatures:

  OVFHardware
  OVFHardwareDataError
"""

import logging

from COT.data_validation import natural_sort
from COT.xml_file import XML

from .item import OVFItem, OVFItemDataError

logger = logging.getLogger(__name__)


class OVFHardwareDataError(Exception):
    """The input data used to construct an :class:`OVFHardware` is not sane."""


class OVFHardware(object):
    """Helper class for :class:`OVF`.

    Represents all hardware items defined by this OVF;
    i.e., the contents of all Items in the VirtualHardwareSection.

    Fundamentally it's just a dict of :class:`OVFItem` objects with a bunch of
    helper methods.
    """

    def __init__(self, ovf):
        """Construct an OVFHardware object describing all Items in the OVF.

        :raise OVFHardwareDataError: if any data errors are seen
        """
        self.ovf = ovf
        self.item_dict = {}
        valid_profiles = set(ovf.config_profiles)
        item_count = 0
        for item in ovf.virtual_hw_section:
            ns = ovf.namespace_for_item_tag(item.tag)
            if not ns:
                continue
            item_count += 1
            # We index the dict by InstanceID as it's the one property of
            # an Item that uniquely identifies this set of hardware items.
            instance = item.find(ns + self.ovf.INSTANCE_ID).text

            # Pre-sanity check - are all of the profiles associated with this
            # item properly defined in the OVF DeploymentOptionSection?
            item_profiles = set(item.get(self.ovf.ITEM_CONFIG, "").split())
            unknown_profiles = item_profiles - valid_profiles
            if unknown_profiles:
                raise OVFHardwareDataError("Unknown profile(s) {0} for "
                                           "Item instance {1}"
                                           .format(unknown_profiles, instance))

            if instance not in self.item_dict:
                self.item_dict[instance] = OVFItem(self.ovf, item)
            else:
                try:
                    self.item_dict[instance].add_item(item)
                except OVFItemDataError as e:
                    logger.debug(e)
                    # Mask away the nitty-gritty details from our caller
                    raise OVFHardwareDataError("Data conflict for instance {0}"
                                               .format(instance))
        logger.verbose(
            "OVF contains %s hardware Item elements describing %s "
            "unique devices", item_count, len(self.item_dict))
        # Treat the current state as golden:
        for ovfitem in self.item_dict.values():
            ovfitem.modified = False

    def update_xml(self):
        """Regenerate all Items under the VirtualHardwareSection, if needed.

        Will do nothing if no Items have been changed.
        """
        modified = False
        if len(self.item_dict) != len(XML.find_all_children(
                self.ovf.virtual_hw_section,
                set([self.ovf.ITEM, self.ovf.STORAGE_ITEM,
                     self.ovf.ETHERNET_PORT_ITEM]))):
            modified = True
        else:
            for ovfitem in self.item_dict.values():
                if ovfitem.modified:
                    modified = True
                    break
        if not modified:
            logger.debug("No changes to hardware definition, "
                         "so no XML update is required")
            return
        # Delete the existing Items:
        delete_count = 0
        for item in list(self.ovf.virtual_hw_section):
            if (item.tag == self.ovf.ITEM or
                    item.tag == self.ovf.STORAGE_ITEM or
                    item.tag == self.ovf.ETHERNET_PORT_ITEM):
                self.ovf.virtual_hw_section.remove(item)
                delete_count += 1
        logger.verbose("Cleared %d existing items from VirtualHWSection",
                       delete_count)
        # Generate the new XML Items, in appropriately sorted order by Instance
        ordering = [self.ovf.INFO, self.ovf.SYSTEM, self.ovf.ITEM]
        for instance in natural_sort(self.item_dict.keys()):
            logger.debug("Writing Item(s) with InstanceID %s", instance)
            ovfitem = self.item_dict[instance]
            new_items = ovfitem.generate_items()
            logger.debug("Generated %d items", len(new_items))
            for item in new_items:
                XML.add_child(self.ovf.virtual_hw_section, item, ordering)
        logger.verbose("Updated XML VirtualHardwareSection, now contains %d "
                       "Items representing %d devices",
                       len(self.ovf.virtual_hw_section.findall(self.ovf.ITEM)),
                       len(self.item_dict))

    def find_unused_instance_id(self):
        """Find the first available ``InstanceID`` number.

        :rtype: string
        """
        i = 1
        while str(i) in self.item_dict.keys():
            i += 1
        logger.debug("Found unused InstanceID %d", i)
        return str(i)

    def new_item(self, resource_type, profile_list=None):
        """Create a new :class:`OVFItem` of the given type.

        :param str resource_type:
        :param list profile_list: Profiles the new item should belong to
        :return: ``(instance, ovfitem)``
        """
        instance = self.find_unused_instance_id()
        ovfitem = OVFItem(self.ovf)
        ovfitem.set_property(self.ovf.INSTANCE_ID, instance, profile_list)
        ovfitem.set_property(self.ovf.RESOURCE_TYPE,
                             self.ovf.RES_MAP[resource_type],
                             profile_list)
        # ovftool freaks out if we leave out the ElementName on an Item,
        # so provide a simple default value.
        ovfitem.set_property(self.ovf.ELEMENT_NAME, resource_type,
                             profile_list)
        self.item_dict[instance] = ovfitem
        ovfitem.modified = True
        logger.info("Added new %s under %s, instance is %s",
                    resource_type, profile_list, instance)
        return (instance, ovfitem)

    def delete_item(self, item):
        """Delete the given :class:`OVFItem`."""
        instance = item.get_value(self.ovf.INSTANCE_ID)
        if self.item_dict[instance] == item:
            del self.item_dict[instance]
        # TODO: error handling - currently a no-op if item not in item_dict

    def clone_item(self, parent_item, profile_list):
        """Clone an :class:`OVFItem` to create a new instance.

        :param OVFItem parent_item: Instance to clone from
        :param list profile_list: List of profiles to clone into
        :return: ``(instance, ovfitem)``
        """
        instance = self.find_unused_instance_id()
        ovfitem = OVFItem(self.ovf)
        for profile in profile_list:
            ovfitem.add_profile(profile, from_item=parent_item)
        ovfitem.set_property(self.ovf.INSTANCE_ID, instance, profile_list)
        ovfitem.modified = True
        self.item_dict[instance] = ovfitem
        logger.debug("Added clone of %s under %s, instance is %s",
                     parent_item, profile_list, instance)
        return (instance, ovfitem)

    def item_match(self, item, resource_type, properties, profile_list):
        """Check whether the given item matches the given filters."""
        if resource_type and (self.ovf.RES_MAP[resource_type] !=
                              item.get_value(self.ovf.RESOURCE_TYPE)):
            return False
        if profile_list:
            for profile in profile_list:
                if not item.has_profile(profile):
                    return False
        for (prop, value) in properties.items():
            if item.get_value(prop) != value:
                return False
        return True

    def find_all_items(self, resource_type=None, properties=None,
                       profile_list=None):
        """Find all items matching the given type, properties, and profiles.

        :param str resource_type: Resource type string like 'scsi' or 'serial'
        :param properties: Property values to match
        :type properties: dict[property, value]
        :param list profile_list: List of profiles to filter on
        :return: list of :class:`OVFItem` instances
        """
        items = [self.item_dict[instance] for instance in
                 natural_sort(self.item_dict.keys())]
        filtered_items = []
        if properties is None:
            properties = {}
        for item in items:
            if self.item_match(item, resource_type, properties, profile_list):
                filtered_items.append(item)
        logger.debug("Found %s %s Items", len(filtered_items), resource_type)
        return filtered_items

    def find_item(self, resource_type=None, properties=None, profile=None):
        """Find the only :class:`OVFItem` of the given :attr:`resource_type`.

        :param str resource_type: Resource type string like 'scsi' or 'serial'
        :param properties: Property values to match
        :type properties: dict[property, value]
        :param str profile: Single profile ID to search within
        :rtype: :class:`OVFItem` or ``None``
        :raise LookupError: if more than one such Item exists.
        """
        matches = self.find_all_items(resource_type, properties, [profile])
        if len(matches) > 1:
            raise LookupError("Found multiple matching {0} Items:\n{2}"
                              .format(resource_type, "\n".join(matches)))
        elif len(matches) == 0:
            return None
        else:
            return matches[0]

    def get_item_count(self, resource_type, profile):
        """Wrapper for :meth:`get_item_count_per_profile`.

        :param str resource_type:
        :param str profile: Single profile identifier string to look up.
        :return: Number of items of this type in this profile.
        """
        return (self.get_item_count_per_profile(resource_type, [profile])
                [profile])

    def get_item_count_per_profile(self, resource_type, profile_list):
        """Get the number of Items of the given type per profile.

        Items present under "no profile" will be counted against
        the total for each profile.

        :param str resource_type:
        :param list profile_list: List of profiles to filter on
          (default: apply across all profiles)
        :rtype: dict[profile, count]
        """
        count_dict = {}
        if not profile_list:
            # Get the count under all profiles
            profile_list = self.ovf.config_profiles + [None]
        for profile in profile_list:
            count_dict[profile] = 0
        for ovfitem in self.find_all_items(resource_type):
            for profile in profile_list:
                if ovfitem.has_profile(profile):
                    count_dict[profile] += 1
        for (profile, count) in count_dict.items():
            logger.debug("Profile '%s' has %s %s Item(s)",
                         profile, count, resource_type)
        return count_dict

    def update_existing_item_count_per_profile(self, resource_type,
                                               count, profile_list):
        """Change profile membership of existing items as needed.

        Helper method for :meth:`set_item_count_per_profile`.

        :return: (count_dict, items_to_add, last_item)
        """
        count_dict = self.get_item_count_per_profile(resource_type,
                                                     profile_list)
        items_seen = dict.fromkeys(profile_list, 0)
        last_item = None

        # First, iterate over existing Items.
        # Once we've seen "count" items under a profile, remove all subsequent
        # items from this profile.
        # If we don't have enough items under a profile, add any items found
        # under other profiles to this profile as well.
        for ovfitem in self.find_all_items(resource_type):
            last_item = ovfitem
            for profile in profile_list:
                if ovfitem.has_profile(profile):
                    if items_seen[profile] >= count:
                        # Too many items - remove this one!
                        ovfitem.remove_profile(profile)
                    else:
                        items_seen[profile] += 1
                else:
                    if count_dict[profile] < count:
                        # Add this profile to this Item
                        ovfitem.add_profile(profile)
                        count_dict[profile] += 1
                        items_seen[profile] += 1

        # How many new Items do we need to create in total?
        items_to_add = 0
        for profile in profile_list:
            delta = count - items_seen[profile]
            if delta > items_to_add:
                items_to_add = delta

        return count_dict, items_to_add, last_item

    def _update_cloned_item(self, new_item, new_item_profiles, item_count):
        """Update a cloned item to make it distinct from its parent.

        Helper method for :meth:`set_item_count_per_profile`.
        """
        resource_type = self.ovf.get_type_from_device(new_item)
        address = new_item.get(self.ovf.ADDRESS)
        if address:
            raise NotImplementedError("Don't know how to ensure a unique "
                                      "Address value when cloning an Item "
                                      "of type {0}".format(resource_type))

        address_on_parent = new_item.get(self.ovf.ADDRESS_ON_PARENT)
        if address_on_parent:
            address_list = new_item.get_all_values(self.ovf.ADDRESS_ON_PARENT)
            if len(address_list) > 1:
                raise NotImplementedError("AddressOnParent is not common "
                                          "across all profiles but has "
                                          "multiple values {0}. COT can't "
                                          "handle this yet."
                                          .format(address_list))
            address_on_parent = address_list[0]
            # Currently we only handle integer addresses
            try:
                address_on_parent = int(address_on_parent)
                address_on_parent += 1
                new_item.set_property(self.ovf.ADDRESS_ON_PARENT,
                                      str(address_on_parent),
                                      new_item_profiles)
            except ValueError:
                raise NotImplementedError("Don't know how to ensure a "
                                          "unique AddressOnParent value "
                                          "given base value '{0}'"
                                          .format(address_on_parent))

        if resource_type == 'ethernet':
            # Update ElementName to reflect the NIC number
            element_name = self.ovf.platform.guess_nic_name(item_count)
            new_item.set_property(self.ovf.ELEMENT_NAME, element_name,
                                  new_item_profiles)

        return new_item

    def set_item_count_per_profile(self, resource_type, count, profile_list):
        """Set the number of items of a given type under the given profile(s).

        If the new count is greater than the current count under this
        profile, then additional instances that already exist under
        another profile will be added to this profile, starting with
        the lowest-sequence instance not already present, and only as
        a last resort will new instances be created.

        If the new count is less than the current count under this profile,
        then the highest-numbered instances will be removed preferentially.

        :param str resource_type: 'cpu', 'harddisk', etc.
        :param int count: Desired number of items
        :param list profile_list: List of profiles to filter on
          (default: apply across all profiles)
        """
        if not profile_list:
            # Set the profile list for all profiles, including the default
            profile_list = self.ovf.config_profiles + [None]

        count_dict, items_to_add, last_item = \
            self.update_existing_item_count_per_profile(
                resource_type, count, profile_list)

        logger.debug("Creating %d new items", items_to_add)
        while items_to_add > 0:
            # Which profiles does this Item need to belong to?
            new_item_profiles = []
            for profile in profile_list:
                if count_dict[profile] < count:
                    new_item_profiles.append(profile)
                    count_dict[profile] += 1
            if last_item is None:
                logger.warning("No existing items of type %s found. "
                               "Will create new %s from scratch.",
                               resource_type, resource_type)
                (_, new_item) = self.new_item(resource_type, new_item_profiles)
            else:
                (_, new_item) = self.clone_item(last_item, new_item_profiles)
            # Check/update other properties of the clone that should be unique:
            # TODO - we assume that the count is the same across profiles
            new_item = self._update_cloned_item(
                new_item, new_item_profiles, count_dict[new_item_profiles[0]])

            last_item = new_item
            items_to_add -= 1

    def set_value_for_all_items(self, resource_type, prop_name, new_value,
                                profile_list, create_new=False):
        """Set a property to the given value for all items of the given type.

        If no items of the given type exist, will create a new ``Item`` if
        :attr:`create_new` is set to ``True``; otherwise will log a warning
        and do nothing.

        :param str resource_type: Resource type such as 'cpu' or 'harddisk'
        :param str prop_name: Property name to update
        :param str new_value: New value to set the property to
        :param list profile_list: List of profiles to filter on
          (default: apply across all profiles)
        :param boolean create_new: Whether to create a new entry if no items
          of this :attr:`resource_type` presently exist.
        """
        ovfitem_list = self.find_all_items(resource_type)
        if not ovfitem_list:
            if not create_new:
                logger.warning("No items of type %s found. Nothing to do.",
                               resource_type)
                return
            logger.warning("No existing items of type %s found. "
                           "Will create new %s from scratch.",
                           resource_type, resource_type)
            (_, ovfitem) = self.new_item(resource_type, profile_list)
            ovfitem_list = [ovfitem]
        for ovfitem in ovfitem_list:
            ovfitem.set_property(prop_name, new_value, profile_list)
        logger.info("Updated %s %s to %s under %s",
                    resource_type, prop_name, new_value, profile_list)

    def set_item_values_per_profile(self, resource_type, prop_name, value_list,
                                    profile_list, default=None):
        """Set value(s) for a property of multiple items of a type.

        :param str resource_type: Device type such as 'harddisk' or 'cpu'
        :param str prop_name: Property name to update
        :param list value_list: List of values to set (one value per item
          of the given :attr:`resource_type`)
        :param list profile_list: List of profiles to filter on
          (default: apply across all profiles)
        :param str default: If there are more matching items than entries in
          :attr:`value_list`, set extra items to this value
        """
        if profile_list is None:
            profile_list = self.ovf.config_profiles + [None]
        for ovfitem in self.find_all_items(resource_type):
            if len(value_list):
                new_value = value_list.pop(0)
            else:
                new_value = default
            for profile in profile_list:
                if ovfitem.has_profile(profile):
                    ovfitem.set_property(prop_name, new_value, [profile])
            logger.info("Updated %s property %s to %s under %s",
                        resource_type, prop_name, new_value, profile_list)
        if len(value_list):
            logger.error("After scanning all known %s Items, not all "
                         "%s values were used - leftover %s",
                         resource_type, prop_name, value_list)
